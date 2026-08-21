from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace
from statistics import NormalDist
from typing import Any

from .ml_contracts import SelectiveThresholds, canonical_contract_json


CALIBRATION_SCHEMA = "reprocheck.selective-calibration.v1"
CALIBRATION_FIELDS = {
    "claim_id",
    "owner_id",
    "split",
    "claim_probability",
    "tuple_probability",
    "evidence_probability",
    "completeness",
    "rank_margin",
    "ood_score",
    "gate_eligible",
    "correct",
}


@dataclass(frozen=True)
class CalibrationResult:
    schema_version: str
    status: str
    corpus_sha256: str
    split_sha256: str
    model_sha256: str
    target_precision: float
    target_wilson_lower: float
    minimum_decisions: int
    minimum_owners: int
    shared_reliability_threshold: float
    thresholds: SelectiveThresholds
    validation_record_count: int
    validation_owner_count: int
    selected_count: int
    selected_owner_count: int
    correct_count: int
    precision: float
    precision_wilson_low: float
    precision_wilson_high: float
    candidate_coverage: float
    calibration_data_sha256: str
    calibration_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "corpus_sha256": self.corpus_sha256,
            "split_sha256": self.split_sha256,
            "model_sha256": self.model_sha256,
            "target_precision": self.target_precision,
            "target_wilson_lower": self.target_wilson_lower,
            "minimum_decisions": self.minimum_decisions,
            "minimum_owners": self.minimum_owners,
            "shared_reliability_threshold": self.shared_reliability_threshold,
            "thresholds": self.thresholds,
            "validation_record_count": self.validation_record_count,
            "validation_owner_count": self.validation_owner_count,
            "selected_count": self.selected_count,
            "selected_owner_count": self.selected_owner_count,
            "correct_count": self.correct_count,
            "precision": self.precision,
            "precision_wilson_low": self.precision_wilson_low,
            "precision_wilson_high": self.precision_wilson_high,
            "candidate_coverage": self.candidate_coverage,
            "calibration_data_sha256": self.calibration_data_sha256,
            "calibration_sha256": self.calibration_sha256,
        }


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if successes < 0 or total < 0 or successes > total:
        raise ValueError("Wilson counts must satisfy 0 <= successes <= total")
    if not 0 < confidence < 1:
        raise ValueError("Wilson confidence must be between 0 and 1")
    if total == 0:
        return 0.0, 1.0
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def reliability_score(record: dict[str, Any]) -> float:
    values = []
    for name in (
        "claim_probability",
        "tuple_probability",
        "evidence_probability",
        "completeness",
        "rank_margin",
    ):
        value = float(record[name])
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be finite and between 0 and 1")
        values.append(value)
    ood_score = float(record["ood_score"])
    if not math.isfinite(ood_score) or not 0 <= ood_score <= 1:
        raise ValueError("ood_score must be finite and between 0 and 1")
    values.append(1 - ood_score)
    return min(values)


def _validate_digest(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _validate_calibration_records(records: list[dict[str, object]]) -> None:
    if not records:
        raise ValueError("calibration requires at least one validation record")
    claim_ids: set[str] = set()
    for record in records:
        if set(record) != CALIBRATION_FIELDS:
            raise ValueError("calibration records must contain the exact declared fields")
        if record["split"] != "validation":
            raise ValueError("calibration may use only the validation split")
        claim_id, owner_id = str(record["claim_id"]), str(record["owner_id"])
        if not claim_id or claim_id in claim_ids:
            raise ValueError("calibration claim_id values must be non-empty and unique")
        if not owner_id:
            raise ValueError("calibration owner_id must be non-empty")
        claim_ids.add(claim_id)
        if not isinstance(record["gate_eligible"], bool) or not isinstance(record["correct"], bool):
            raise ValueError("calibration gate_eligible and correct fields must be boolean")
        reliability_score(record)


def _thresholds(shared: float) -> SelectiveThresholds:
    review = shared * 0.6
    return SelectiveThresholds(
        verify_claim_probability=shared,
        verify_tuple_probability=shared,
        verify_evidence_probability=shared,
        review_claim_probability=review,
        review_tuple_probability=review,
        review_evidence_probability=review,
        minimum_completeness=shared,
        minimum_rank_margin=shared,
        maximum_ood_score=1 - shared,
    )


def calibrate_selective_thresholds(
    records: list[dict[str, object]],
    *,
    corpus_sha256: str,
    split_sha256: str,
    model_sha256: str,
    target_precision: float = 0.95,
    target_wilson_lower: float = 0.90,
    minimum_decisions: int = 20,
    minimum_owners: int = 10,
) -> CalibrationResult:
    for value, label in (
        (corpus_sha256, "corpus_sha256"),
        (split_sha256, "split_sha256"),
        (model_sha256, "model_sha256"),
    ):
        _validate_digest(value, label)
    if not 0 <= target_wilson_lower <= target_precision <= 1:
        raise ValueError("calibration precision targets must satisfy 0 <= lower <= point <= 1")
    if minimum_decisions < 1 or minimum_owners < 1:
        raise ValueError("calibration minimum information values must be positive")
    _validate_calibration_records(records)
    normalized = sorted(records, key=lambda item: str(item["claim_id"]))
    calibration_data_sha256 = hashlib.sha256(
        canonical_contract_json(normalized).encode("utf-8")
    ).hexdigest()
    candidates = sorted({reliability_score(record) for record in records}, reverse=True)
    feasible: list[tuple[int, float, float, int, int, float, float, set[str]]] = []
    for threshold in candidates:
        selected = [
            record
            for record in records
            if record["gate_eligible"] and reliability_score(record) >= threshold
        ]
        correct = sum(bool(record["correct"]) for record in selected)
        owners = {str(record["owner_id"]) for record in selected}
        low, high = wilson_interval(correct, len(selected))
        precision = correct / len(selected) if selected else 0.0
        if (
            len(selected) >= minimum_decisions
            and len(owners) >= minimum_owners
            and precision >= target_precision
            and low >= target_wilson_lower
        ):
            feasible.append(
                (len(selected), precision, threshold, correct, len(owners), low, high, owners)
            )
    if feasible:
        selected_count, precision, threshold, correct_count, owner_count, low, high, _ = max(
            feasible, key=lambda item: (item[0], item[1], item[2])
        )
        status = "calibrated"
    else:
        selected_count = correct_count = owner_count = 0
        precision, threshold, low, high = 0.0, 1.0, 0.0, 1.0
        status = "insufficient_calibration"
    result = CalibrationResult(
        schema_version=CALIBRATION_SCHEMA,
        status=status,
        corpus_sha256=corpus_sha256,
        split_sha256=split_sha256,
        model_sha256=model_sha256,
        target_precision=target_precision,
        target_wilson_lower=target_wilson_lower,
        minimum_decisions=minimum_decisions,
        minimum_owners=minimum_owners,
        shared_reliability_threshold=threshold,
        thresholds=_thresholds(threshold),
        validation_record_count=len(records),
        validation_owner_count=len({str(record["owner_id"]) for record in records}),
        selected_count=selected_count,
        selected_owner_count=owner_count,
        correct_count=correct_count,
        precision=precision,
        precision_wilson_low=low,
        precision_wilson_high=high,
        candidate_coverage=selected_count / len(records),
        calibration_data_sha256=calibration_data_sha256,
        calibration_sha256="",
    )
    digest = _calibration_digest(result)
    return replace(result, calibration_sha256=digest)


def _calibration_digest(result: CalibrationResult) -> str:
    payload = result.to_dict()
    payload["calibration_sha256"] = ""
    return hashlib.sha256(canonical_contract_json(payload).encode("utf-8")).hexdigest()


def verify_calibration(result: CalibrationResult) -> list[str]:
    errors: list[str] = []
    try:
        for value, label in (
            (result.corpus_sha256, "corpus_sha256"),
            (result.split_sha256, "split_sha256"),
            (result.model_sha256, "model_sha256"),
            (result.calibration_data_sha256, "calibration_data_sha256"),
            (result.calibration_sha256, "calibration_sha256"),
        ):
            _validate_digest(value, label)
    except ValueError as error:
        errors.append(str(error))
    if result.calibration_sha256 != _calibration_digest(result):
        errors.append("calibration digest does not match")
    if result.status not in {"calibrated", "insufficient_calibration"}:
        errors.append("calibration status is invalid")
    if result.status == "calibrated" and result.selected_count < result.minimum_decisions:
        errors.append("calibrated result does not meet minimum_decisions")
    return errors
