from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType
from typing import Any, Literal, Mapping


CONTEXT_FIELDS = frozenset({"model", "dataset", "split", "task", "experiment", "run", "variant"})
EvidenceGrade = Literal["raw_recomputed", "structured_reported", "text_reported"]
MLAction = Literal["verify", "review", "abstain"]
_SOURCE_NUMBER = re.compile(
    r"^[+\-−]?(?:(?:\d{1,3}(?:,\d{3})+)(?:\.\d+)?|\d+(?:[.,]\d*)?|[.,]\d+)"
    r"(?:[eE][+\-−]?\d+)?\s*%?$"
)


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


def _require_probability(value: float, field_name: str) -> float:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be finite and between 0 and 1")
    return value


def _normalize_context(value: Mapping[str, str]) -> Mapping[str, str]:
    unsupported = sorted(set(value) - CONTEXT_FIELDS)
    if unsupported:
        raise ValueError(f"unsupported context fields: {', '.join(unsupported)}")
    normalized: dict[str, str] = {}
    for key, item in sorted(value.items()):
        normalized[key] = _require_text(str(item), f"context {key}")
    return MappingProxyType(normalized)


def _validate_span(span: tuple[int, int], source: str, field_name: str) -> None:
    if len(span) != 2 or span[0] < 0 or span[1] <= span[0] or span[1] > len(source):
        raise ValueError(f"{field_name} must be a valid non-empty source span")


def _source_number(value: str) -> float:
    token = value.strip().replace("−", "-").removesuffix("%").strip()
    if "," in token and "." in token:
        token = token.replace(",", "")
    elif "," in token:
        if re.fullmatch(r"[+\-]?\d{1,3}(?:,\d{3})+", token):
            token = token.replace(",", "")
        else:
            token = token.replace(",", ".")
    return float(token)


@dataclass(frozen=True)
class MLClaimTuple:
    claim_id: str
    metric: str
    value: float
    unit: Literal["scalar", "percent"]
    source_text: str
    metric_span: tuple[int, int]
    value_span: tuple[int, int]
    context: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _require_text(self.claim_id, "claim_id"))
        object.__setattr__(self, "metric", _require_text(self.metric, "metric").casefold())
        object.__setattr__(self, "source_text", _require_text(self.source_text, "source_text"))
        if not math.isfinite(self.value):
            raise ValueError("claim value must be finite")
        if self.unit not in {"scalar", "percent"}:
            raise ValueError("claim unit must be scalar or percent")
        object.__setattr__(self, "metric_span", tuple(self.metric_span))
        object.__setattr__(self, "value_span", tuple(self.value_span))
        _validate_span(self.metric_span, self.source_text, "metric_span")
        _validate_span(self.value_span, self.source_text, "value_span")
        if not self.metric_text.strip():
            raise ValueError("metric_span must bind non-empty source text")
        if not _SOURCE_NUMBER.fullmatch(self.value_text.strip()):
            raise ValueError("value_span must bind a numeric source token")
        source_value = _source_number(self.value_text)
        normalized_percent = source_value / 100
        if not math.isclose(source_value, self.value, rel_tol=1e-12, abs_tol=1e-12) and not (
            (self.value_text.strip().endswith("%") or self.unit == "percent")
            and math.isclose(normalized_percent, self.value, rel_tol=1e-12, abs_tol=1e-12)
        ):
            raise ValueError("claim value does not match its numeric source span")
        object.__setattr__(self, "context", _normalize_context(self.context))

    @property
    def metric_text(self) -> str:
        return self.source_text[self.metric_span[0] : self.metric_span[1]]

    @property
    def value_text(self) -> str:
        return self.source_text[self.value_span[0] : self.value_span[1]]


@dataclass(frozen=True)
class EvidenceCandidate:
    candidate_id: str
    artifact_id: str
    evidence_grade: EvidenceGrade
    metric: str | None
    value: float | None
    context: Mapping[str, str]
    rank_score: float
    rank_margin: float
    integrity_verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _require_text(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "artifact_id", _require_text(self.artifact_id, "artifact_id"))
        if self.evidence_grade not in {
            "raw_recomputed",
            "structured_reported",
            "text_reported",
        }:
            raise ValueError("unsupported evidence_grade")
        if self.metric is not None:
            object.__setattr__(self, "metric", _require_text(self.metric, "metric").casefold())
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("evidence value must be finite")
        _require_probability(self.rank_score, "rank_score")
        _require_probability(self.rank_margin, "rank_margin")
        if not isinstance(self.integrity_verified, bool):
            raise ValueError("integrity_verified must be boolean")
        object.__setattr__(self, "context", _normalize_context(self.context))


@dataclass(frozen=True)
class ModelScores:
    claim_probability: float
    tuple_probability: float
    evidence_probability: float
    out_of_distribution_score: float
    rule_agreement: bool

    def __post_init__(self) -> None:
        for field_name in (
            "claim_probability",
            "tuple_probability",
            "evidence_probability",
            "out_of_distribution_score",
        ):
            _require_probability(float(getattr(self, field_name)), field_name)
        if not isinstance(self.rule_agreement, bool):
            raise ValueError("rule_agreement must be boolean")


@dataclass(frozen=True)
class SelectiveThresholds:
    verify_claim_probability: float
    verify_tuple_probability: float
    verify_evidence_probability: float
    review_claim_probability: float
    review_tuple_probability: float
    review_evidence_probability: float
    minimum_completeness: float
    minimum_rank_margin: float
    maximum_ood_score: float

    def __post_init__(self) -> None:
        for item in fields(self):
            _require_probability(float(getattr(self, item.name)), item.name)
        pairs = (
            (self.review_claim_probability, self.verify_claim_probability, "claim"),
            (self.review_tuple_probability, self.verify_tuple_probability, "tuple"),
            (self.review_evidence_probability, self.verify_evidence_probability, "evidence"),
        )
        for review, verify, name in pairs:
            if review > verify:
                raise ValueError(f"{name} review threshold cannot exceed verify threshold")


@dataclass(frozen=True)
class CompatibilityResult:
    compatible: bool
    completeness: float
    matched: tuple[str, ...]
    missing: tuple[str, ...]
    conflicts: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_probability(self.completeness, "completeness")
        if self.compatible == bool(self.conflicts):
            raise ValueError("compatibility must be false exactly when conflicts are present")


@dataclass(frozen=True)
class SelectiveDecision:
    action: MLAction
    reasons: tuple[str, ...]
    compatibility: CompatibilityResult
    final_verdict: None = None

    def __post_init__(self) -> None:
        if self.action not in {"verify", "review", "abstain"}:
            raise ValueError("unsupported selective action")
        if not self.reasons:
            raise ValueError("selective decision must contain at least one reason")
        if self.final_verdict is not None:
            raise ValueError("ML decisions cannot contain a final evidence verdict")


def _to_primitive(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _to_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("contract numbers must be finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported contract value: {type(value).__name__}")


def canonical_contract_json(value: Any) -> str:
    return json.dumps(
        _to_primitive(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
