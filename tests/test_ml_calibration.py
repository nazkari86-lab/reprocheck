from __future__ import annotations

import copy

import pytest

from reprocheck.ml_calibration import calibrate_selective_thresholds, verify_calibration


def _record(
    index: int, score: float, correct: bool, *, split: str = "validation"
) -> dict[str, object]:
    return {
        "claim_id": f"claim-{index}",
        "owner_id": f"owner-{index // 2}",
        "split": split,
        "claim_probability": score,
        "tuple_probability": score,
        "evidence_probability": score,
        "completeness": score,
        "rank_margin": score,
        "ood_score": 1 - score,
        "gate_eligible": True,
        "correct": correct,
    }


def test_calibration_maximizes_coverage_under_precision_constraint() -> None:
    records = [
        _record(0, 0.99, True),
        _record(1, 0.96, True),
        _record(2, 0.93, True),
        _record(3, 0.90, True),
        _record(4, 0.80, False),
        _record(5, 0.70, False),
    ]
    result = calibrate_selective_thresholds(
        records,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        model_sha256="c" * 64,
        target_precision=0.95,
        target_wilson_lower=0.0,
        minimum_decisions=3,
        minimum_owners=2,
    )
    assert result.status == "calibrated"
    assert result.selected_count == 4
    assert result.correct_count == 4
    assert result.shared_reliability_threshold == 0.9
    assert result.thresholds.verify_claim_probability == 0.9
    assert verify_calibration(result) == []


def test_calibration_fails_closed_when_no_threshold_has_enough_information() -> None:
    result = calibrate_selective_thresholds(
        [_record(0, 0.9, False), _record(1, 0.8, True)],
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        model_sha256="c" * 64,
        target_precision=1.0,
        target_wilson_lower=0.9,
        minimum_decisions=3,
        minimum_owners=1,
    )
    assert result.status == "insufficient_calibration"
    assert result.selected_count == 0
    assert result.thresholds.verify_claim_probability == 1.0


def test_calibration_rejects_test_labels_duplicate_claims_and_tamper() -> None:
    records = [_record(0, 0.9, True), _record(1, 0.8, False)]
    records[0]["split"] = "test"
    with pytest.raises(ValueError, match="validation split"):
        calibrate_selective_thresholds(
            records,
            corpus_sha256="a" * 64,
            split_sha256="b" * 64,
            model_sha256="c" * 64,
            minimum_decisions=1,
            minimum_owners=1,
        )

    records = [_record(0, 0.9, True), _record(0, 0.8, False)]
    with pytest.raises(ValueError, match="claim_id"):
        calibrate_selective_thresholds(
            records,
            corpus_sha256="a" * 64,
            split_sha256="b" * 64,
            model_sha256="c" * 64,
            minimum_decisions=1,
            minimum_owners=1,
        )

    valid = calibrate_selective_thresholds(
        [_record(0, 0.9, True), _record(1, 0.8, False)],
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        model_sha256="c" * 64,
        target_precision=1.0,
        target_wilson_lower=0.0,
        minimum_decisions=1,
        minimum_owners=1,
    )
    tampered = copy.copy(valid)
    object.__setattr__(tampered, "selected_count", valid.selected_count + 1)
    assert any("digest does not match" in error for error in verify_calibration(tampered))
