from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from typing import Any

from .ml_calibration import (
    CalibrationResult,
    reliability_score,
    verify_calibration,
    wilson_interval,
)
from .ml_contracts import canonical_contract_json


EVALUATION_FIELDS = {
    "claim_id",
    "owner_id",
    "split",
    "language",
    "domain",
    "eligible_claim",
    "claim_probability",
    "tuple_probability",
    "evidence_probability",
    "completeness",
    "rank_margin",
    "ood_score",
    "gate_eligible",
    "prediction_correct",
    "baseline_selected",
    "baseline_correct",
}
SUCCESS_FIELDS = {
    "minimum_owners",
    "minimum_eligible_claims",
    "minimum_recall_delta",
    "minimum_precision",
    "minimum_precision_wilson_lower",
    "minimum_claim_coverage",
}


def _validate_records(records: list[dict[str, object]], phase: str) -> None:
    if phase not in {"test", "prospective"}:
        raise ValueError("evaluation phase must be test or prospective")
    if not records:
        raise ValueError("frozen evaluation requires at least one record")
    claim_ids: set[str] = set()
    for record in records:
        if set(record) != EVALUATION_FIELDS:
            raise ValueError("evaluation records must contain the exact declared fields")
        if record["split"] != phase:
            raise ValueError(f"{phase} phase may use only {phase} rows")
        claim_id = str(record["claim_id"])
        if not claim_id or claim_id in claim_ids:
            raise ValueError("evaluation claim_id values must be non-empty and unique")
        claim_ids.add(claim_id)
        if not str(record["owner_id"]) or not str(record["language"]) or not str(record["domain"]):
            raise ValueError("evaluation owner, language, and domain must be non-empty")
        for name in (
            "eligible_claim",
            "gate_eligible",
            "prediction_correct",
            "baseline_selected",
            "baseline_correct",
        ):
            if not isinstance(record[name], bool):
                raise ValueError(f"evaluation {name} must be boolean")
        if record["prediction_correct"] and not record["eligible_claim"]:
            raise ValueError("a correct prediction must refer to an eligible claim")
        if record["baseline_correct"] and (
            not record["baseline_selected"] or not record["eligible_claim"]
        ):
            raise ValueError("a correct baseline result must be selected and eligible")
        reliability_score(record)


def _average_precision(scores: list[float], labels: list[bool]) -> float:
    positives = sum(labels)
    if not positives:
        return 0.0
    ordered = sorted(zip(scores, labels), key=lambda item: item[0], reverse=True)
    correct = 0
    total = 0.0
    for rank, (_, label) in enumerate(ordered, start=1):
        if label:
            correct += 1
            total += correct / rank
    return total / positives


def _calibration_metrics(
    scores: list[float], labels: list[bool], bins: int = 10
) -> dict[str, float]:
    if not scores:
        return {"brier": 0.0, "ece": 0.0, "pr_auc": 0.0}
    brier = sum((score - float(label)) ** 2 for score, label in zip(scores, labels)) / len(scores)
    ece = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        members = [
            position
            for position, score in enumerate(scores)
            if low <= score < high or (index == bins - 1 and score == 1)
        ]
        if members:
            confidence = sum(scores[position] for position in members) / len(members)
            accuracy = sum(labels[position] for position in members) / len(members)
            ece += len(members) / len(scores) * abs(confidence - accuracy)
    return {"brier": brier, "ece": ece, "pr_auc": _average_precision(scores, labels)}


def _risk_coverage(records: list[dict[str, object]]) -> list[dict[str, float | int]]:
    scored = [
        (reliability_score(record), bool(record["prediction_correct"]))
        for record in records
        if record["gate_eligible"]
    ]
    points: list[dict[str, float | int]] = []
    for threshold in sorted({score for score, _ in scored}, reverse=True):
        selected = [label for score, label in scored if score >= threshold]
        precision = sum(selected) / len(selected)
        points.append(
            {
                "threshold": threshold,
                "decisions": len(selected),
                "coverage": len(selected) / len(records),
                "risk": 1 - precision,
            }
        )
    return points


def _owner_bootstrap(
    predictions: list[dict[str, Any]], *, samples: int, seed: int
) -> dict[str, float | int]:
    if samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in predictions:
        groups[item["owner_id"]].append(item)
    owners = sorted(groups)
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        selected_owners = [rng.choice(owners) for _ in owners]
        rows = [row for owner in selected_owners for row in groups[owner]]
        eligible = sum(row["eligible_claim"] for row in rows)
        if not eligible:
            continue
        system = sum(row["selected"] and row["prediction_correct"] for row in rows)
        baseline = sum(row["baseline_correct"] for row in rows)
        deltas.append((system - baseline) / eligible)
    if not deltas:
        return {"samples": 0, "low": 0.0, "high": 0.0}
    deltas.sort()
    low_index = max(0, math.floor(0.025 * (len(deltas) - 1)))
    high_index = min(len(deltas) - 1, math.ceil(0.975 * (len(deltas) - 1)))
    return {"samples": len(deltas), "low": deltas[low_index], "high": deltas[high_index]}


def evaluate_frozen_selective(
    records: list[dict[str, object]],
    calibration: CalibrationResult,
    *,
    phase: str,
    bootstrap_samples: int = 1_000,
    bootstrap_seed: int = 20260821,
    success_gate: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    calibration_errors = verify_calibration(calibration)
    if calibration_errors or calibration.status != "calibrated":
        detail = "; ".join(calibration_errors) or calibration.status
        raise ValueError(f"calibration integrity failure: {detail}")
    _validate_records(records, phase)
    gate = success_gate or {
        "minimum_owners": 30,
        "minimum_eligible_claims": 100,
        "minimum_recall_delta": 0.15,
        "minimum_precision": 0.95,
        "minimum_precision_wilson_lower": 0.90,
        "minimum_claim_coverage": 0.70,
    }
    if set(gate) != SUCCESS_FIELDS:
        raise ValueError("success_gate must contain the exact preregistered fields")
    threshold = calibration.shared_reliability_threshold
    predictions: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: str(item["claim_id"])):
        reliability = reliability_score(record)
        selected = bool(record["gate_eligible"]) and reliability >= threshold
        predictions.append(
            {
                "claim_id": record["claim_id"],
                "owner_id": record["owner_id"],
                "language": record["language"],
                "domain": record["domain"],
                "eligible_claim": record["eligible_claim"],
                "reliability": reliability,
                "selected": selected,
                "prediction_correct": record["prediction_correct"],
                "baseline_selected": record["baseline_selected"],
                "baseline_correct": record["baseline_correct"],
            }
        )
    eligible = sum(item["eligible_claim"] for item in predictions)
    selected = sum(item["selected"] for item in predictions)
    selected_eligible = sum(item["selected"] and item["eligible_claim"] for item in predictions)
    true_positive = sum(item["selected"] and item["prediction_correct"] for item in predictions)
    baseline_selected = sum(item["baseline_selected"] for item in predictions)
    baseline_true_positive = sum(item["baseline_correct"] for item in predictions)
    precision = true_positive / selected if selected else 0.0
    recall = true_positive / eligible if eligible else 0.0
    baseline_precision = baseline_true_positive / baseline_selected if baseline_selected else 0.0
    baseline_recall = baseline_true_positive / eligible if eligible else 0.0
    precision_low, precision_high = wilson_interval(true_positive, selected)
    claim_coverage = selected_eligible / eligible if eligible else 0.0
    recall_delta = recall - baseline_recall
    owners = len({str(item["owner_id"]) for item in predictions})
    shortfalls = []
    if owners < int(gate["minimum_owners"]):
        shortfalls.append("owners")
    if eligible < int(gate["minimum_eligible_claims"]):
        shortfalls.append("eligible_claims")
    if shortfalls:
        gate_status = "insufficient_sample"
    else:
        passed = (
            recall_delta >= float(gate["minimum_recall_delta"])
            and precision >= float(gate["minimum_precision"])
            and precision_low >= float(gate["minimum_precision_wilson_lower"])
            and claim_coverage >= float(gate["minimum_claim_coverage"])
        )
        gate_status = "passed" if passed else "failed"
    scores = [float(item["reliability"]) for item in predictions]
    correctness = [bool(item["prediction_correct"]) for item in predictions]
    result: dict[str, Any] = {
        "schema_version": "reprocheck.selective-evaluation.v1",
        "phase": phase,
        "calibration": {
            "calibration_sha256": calibration.calibration_sha256,
            "model_sha256": calibration.model_sha256,
            "corpus_sha256": calibration.corpus_sha256,
            "split_sha256": calibration.split_sha256,
            "shared_reliability_threshold": threshold,
        },
        "counts": {
            "records": len(predictions),
            "owners": owners,
            "eligible_claims": eligible,
            "automatic_decisions": selected,
            "automatic_eligible_claims": selected_eligible,
        },
        "system": {
            "true_positive": true_positive,
            "false_positive": selected - true_positive,
            "precision": precision,
            "precision_wilson_95": [precision_low, precision_high],
            "recall": recall,
            "claim_coverage": claim_coverage,
            "candidate_coverage": selected / len(predictions),
        },
        "baseline": {
            "selected": baseline_selected,
            "true_positive": baseline_true_positive,
            "precision": baseline_precision,
            "recall": baseline_recall,
        },
        "comparison": {
            "recall_delta": recall_delta,
            "owner_bootstrap_95": _owner_bootstrap(
                predictions, samples=bootstrap_samples, seed=bootstrap_seed
            ),
        },
        "calibration_metrics": _calibration_metrics(scores, correctness),
        "risk_coverage": _risk_coverage(records),
        "success_gate": {
            "status": gate_status,
            "criteria": gate,
            "shortfalls": sorted(shortfalls),
        },
        "predictions": predictions,
        "result_sha256": "",
    }
    result["result_sha256"] = hashlib.sha256(
        canonical_contract_json(result).encode("utf-8")
    ).hexdigest()
    return result


def verify_frozen_evaluation(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    digest = result.get("result_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        errors.append("evaluation result digest is malformed")
        return errors
    payload = dict(result)
    payload["result_sha256"] = ""
    expected = hashlib.sha256(canonical_contract_json(payload).encode("utf-8")).hexdigest()
    if digest != expected:
        errors.append("evaluation result digest does not match")
    if result.get("schema_version") != "reprocheck.selective-evaluation.v1":
        errors.append("evaluation result schema is unsupported")
    return errors
