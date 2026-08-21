from __future__ import annotations

import pytest

from reprocheck.ml_calibration import calibrate_selective_thresholds
from reprocheck.ml_evaluation import evaluate_frozen_selective, verify_frozen_evaluation


def _calibration():
    records = []
    for index, (score, correct) in enumerate(
        [(0.99, True), (0.95, True), (0.9, True), (0.8, False)]
    ):
        records.append(
            {
                "claim_id": f"cal-{index}",
                "owner_id": f"cal-owner-{index}",
                "split": "validation",
                "claim_probability": score,
                "tuple_probability": score,
                "evidence_probability": score,
                "completeness": score,
                "rank_margin": score,
                "ood_score": 1 - score,
                "gate_eligible": True,
                "correct": correct,
            }
        )
    return calibrate_selective_thresholds(
        records,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        model_sha256="c" * 64,
        target_precision=1.0,
        target_wilson_lower=0.0,
        minimum_decisions=2,
        minimum_owners=2,
    )


def _evaluation_record(
    index: int,
    score: float,
    *,
    eligible: bool,
    correct: bool,
    baseline_selected: bool,
    baseline_correct: bool,
    split: str = "test",
) -> dict[str, object]:
    return {
        "claim_id": f"test-{index}",
        "owner_id": f"test-owner-{index}",
        "split": split,
        "language": "en" if index % 2 else "ru",
        "domain": "vision" if index % 2 else "nlp",
        "eligible_claim": eligible,
        "claim_probability": score,
        "tuple_probability": score,
        "evidence_probability": score,
        "completeness": score,
        "rank_margin": score,
        "ood_score": 1 - score,
        "gate_eligible": True,
        "prediction_correct": correct,
        "baseline_selected": baseline_selected,
        "baseline_correct": baseline_correct,
    }


def test_frozen_evaluation_reports_precision_recall_calibration_and_predictions() -> None:
    records = [
        _evaluation_record(
            0, 0.99, eligible=True, correct=True, baseline_selected=True, baseline_correct=True
        ),
        _evaluation_record(
            1, 0.96, eligible=True, correct=True, baseline_selected=False, baseline_correct=False
        ),
        _evaluation_record(
            2, 0.93, eligible=True, correct=False, baseline_selected=False, baseline_correct=False
        ),
        _evaluation_record(
            3, 0.20, eligible=False, correct=False, baseline_selected=False, baseline_correct=False
        ),
    ]
    result = evaluate_frozen_selective(
        records,
        _calibration(),
        phase="test",
        bootstrap_samples=200,
        bootstrap_seed=7,
        success_gate={
            "minimum_owners": 4,
            "minimum_eligible_claims": 3,
            "minimum_recall_delta": 0.2,
            "minimum_precision": 0.6,
            "minimum_precision_wilson_lower": 0.0,
            "minimum_claim_coverage": 0.6,
        },
    )
    assert result["counts"]["automatic_decisions"] == 3
    assert result["system"]["precision"] == 2 / 3
    assert result["system"]["recall"] == 2 / 3
    assert result["baseline"]["recall"] == 1 / 3
    assert result["comparison"]["recall_delta"] == 1 / 3
    assert result["success_gate"]["status"] == "passed"
    assert len(result["predictions"]) == 4
    assert result["result_sha256"]
    assert verify_frozen_evaluation(result) == []
    assert result["calibration"]["calibration_sha256"] == _calibration().calibration_sha256

    result["system"]["precision"] = 1.0
    assert "evaluation result digest does not match" in verify_frozen_evaluation(result)


def test_evaluation_cannot_use_validation_rows_or_tampered_calibration() -> None:
    record = _evaluation_record(
        0,
        0.9,
        eligible=True,
        correct=True,
        baseline_selected=False,
        baseline_correct=False,
        split="validation",
    )
    with pytest.raises(ValueError, match="test phase"):
        evaluate_frozen_selective([record], _calibration(), phase="test")

    calibration = _calibration()
    object.__setattr__(calibration, "selected_count", calibration.selected_count + 1)
    record["split"] = "test"
    with pytest.raises(ValueError, match="calibration integrity"):
        evaluate_frozen_selective([record], calibration, phase="test")


def test_success_gate_is_insufficient_before_minimum_sample() -> None:
    result = evaluate_frozen_selective(
        [
            _evaluation_record(
                0,
                0.99,
                eligible=True,
                correct=True,
                baseline_selected=False,
                baseline_correct=False,
                split="prospective",
            )
        ],
        _calibration(),
        phase="prospective",
        bootstrap_samples=20,
        success_gate={
            "minimum_owners": 30,
            "minimum_eligible_claims": 100,
            "minimum_recall_delta": 0.15,
            "minimum_precision": 0.95,
            "minimum_precision_wilson_lower": 0.90,
            "minimum_claim_coverage": 0.70,
        },
    )
    assert result["success_gate"]["status"] == "insufficient_sample"
    assert set(result["success_gate"]["shortfalls"]) == {
        "eligible_claims",
        "owners",
    }
