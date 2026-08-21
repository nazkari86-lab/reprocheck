from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Literal

from .metric_names import canonical_metric
from .ml_contracts import CONTEXT_FIELDS, MLClaimTuple


_NUMBER = re.compile(
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:,\d{3})+)(?:\.\d+)?|"
    r"\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+\-−]?\d+)?\s*%?"
)
_SUPPORTED_METRICS = frozenset(
    {
        "accuracy",
        "precision",
        "recall",
        "specificity",
        "f1",
        "auroc",
        "auprc",
        "log_loss",
        "brier",
        "dice",
        "hard_dice",
        "iou",
        "hard_iou",
        "map",
        "map50",
        "map75",
        "map50_95",
        "mar",
    }
)


@dataclass(frozen=True)
class NumericSpan:
    start: int
    end: int
    raw_text: str
    value: float
    unit: Literal["scalar", "percent"]

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("numeric span must be non-empty and nonnegative")
        if not self.raw_text or not math.isfinite(self.value):
            raise ValueError("numeric span text must be non-empty and value finite")


@dataclass(frozen=True)
class ScoredSpan:
    label: str
    start: int
    end: int
    score: float
    source_text: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("scored span label must be non-empty")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("scored span must be non-empty and nonnegative")
        if not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("scored span score must be finite and between 0 and 1")
        if self.source_text is not None and not self.source_text:
            raise ValueError("declared scored span source_text must be non-empty")


def _parse_source_number(raw_text: str) -> tuple[float, Literal["scalar", "percent"]]:
    percent = raw_text.strip().endswith("%")
    token = raw_text.strip().replace("−", "-").removesuffix("%").strip()
    if "," in token and "." in token:
        token = token.replace(",", "")
    elif "," in token:
        if re.fullmatch(r"[+\-]?\d{1,3}(?:,\d{3})+", token):
            token = token.replace(",", "")
        else:
            token = token.replace(",", ".")
    value = float(token)
    if percent:
        return value / 100, "percent"
    return value, "scalar"


def enumerate_numeric_spans(source_text: str) -> tuple[NumericSpan, ...]:
    spans: list[NumericSpan] = []
    for match in _NUMBER.finditer(source_text):
        raw_text = match.group(0).strip()
        left_trim = len(match.group(0)) - len(match.group(0).lstrip())
        value, unit = _parse_source_number(raw_text)
        if math.isfinite(value):
            start = match.start() + left_trim
            spans.append(NumericSpan(start, start + len(raw_text), raw_text, value, unit))
    return tuple(spans)


def _bound_text(source_text: str, span: ScoredSpan) -> str:
    if span.end > len(source_text):
        raise ValueError("scored span exceeds source text")
    bound = source_text[span.start : span.end]
    if span.source_text is not None and bound != span.source_text:
        raise ValueError("scored span does not bind its declared source_text")
    return bound


def decode_scored_claim(
    *,
    claim_id: str,
    source_text: str,
    numeric_span: NumericSpan,
    metric_spans: list[ScoredSpan],
    context_spans: dict[str, list[ScoredSpan]],
    minimum_score: float = 0.5,
) -> MLClaimTuple | None:
    if not 0 <= minimum_score <= 1:
        raise ValueError("minimum_score must be between 0 and 1")
    if (
        numeric_span.end > len(source_text)
        or source_text[numeric_span.start : numeric_span.end] != numeric_span.raw_text
    ):
        raise ValueError("numeric span does not bind source text")
    unsupported_context = sorted(set(context_spans) - CONTEXT_FIELDS)
    if unsupported_context:
        raise ValueError(f"unsupported context fields: {', '.join(unsupported_context)}")

    eligible_metrics = []
    for span in metric_spans:
        _bound_text(source_text, span)
        metric = canonical_metric(span.label)
        if span.score >= minimum_score and metric in _SUPPORTED_METRICS:
            eligible_metrics.append((span, metric))
    if not eligible_metrics:
        return None
    metric_span, metric = min(
        eligible_metrics,
        key=lambda item: (-item[0].score, item[0].start, item[0].end, item[1]),
    )

    context: dict[str, str] = {}
    for field_name in sorted(context_spans):
        candidates = context_spans[field_name]
        for span in candidates:
            _bound_text(source_text, span)
        eligible = [span for span in candidates if span.score >= minimum_score]
        if eligible:
            selected = min(
                eligible, key=lambda span: (-span.score, span.start, span.end, span.label)
            )
            context[field_name] = _bound_text(source_text, selected)

    return MLClaimTuple(
        claim_id=claim_id,
        metric=metric,
        value=numeric_span.value,
        unit=numeric_span.unit,
        source_text=source_text,
        metric_span=(metric_span.start, metric_span.end),
        value_span=(numeric_span.start, numeric_span.end),
        context=context,
    )


def score_tuple_predictions(
    expected: list[dict[str, Any]], predicted: list[dict[str, Any]]
) -> dict[str, Any]:
    expected_by_id = {str(item["claim_id"]): item for item in expected}
    predicted_by_id = {str(item["claim_id"]): item for item in predicted}
    if len(expected_by_id) != len(expected) or len(predicted_by_id) != len(predicted):
        raise ValueError("tuple scoring requires unique claim_id values")
    fields = ("metric", "value", "context")
    correct = {field: 0 for field in fields}
    exact = 0
    for claim_id, actual in expected_by_id.items():
        candidate = predicted_by_id.get(claim_id)
        if candidate is None:
            continue
        matches = {
            "metric": canonical_metric(str(candidate.get("metric", "")))
            == canonical_metric(str(actual["metric"])),
            "value": _equal_value(candidate.get("value"), actual["value"]),
            "context": candidate.get("context") == actual.get("context"),
        }
        for field, is_correct in matches.items():
            correct[field] += int(is_correct)
        exact += int(all(matches.values()))
    total = len(expected)
    return {
        "expected": total,
        "predicted": len(predicted),
        "exact_count": exact,
        "exact_match": exact / total if total else 0.0,
        "field_accuracy": {field: correct[field] / total if total else 0.0 for field in fields},
    }


def _equal_value(left: Any, right: Any) -> bool:
    try:
        left_number, right_number = float(left), float(right)
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(left_number)
        and math.isfinite(right_number)
        and math.isclose(left_number, right_number, rel_tol=1e-12, abs_tol=1e-12)
    )
