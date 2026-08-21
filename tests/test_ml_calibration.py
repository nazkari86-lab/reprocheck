from __future__ import annotations

import copy

import pytest

from reprocheck.ml_calibration import (
    calibrate_selective_thresholds,
    reliability_score,
    verify_calibration,
    wilson_interval,
)


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


@pytest.mark.parametrize(
    ("records", "kwargs", "message"),
    [
        ([], {}, "at least one"),
        ([_record(0, 0.9, True)], {"corpus_sha256": "bad"}, "SHA-256"),
        ([_record(0, 0.9, True)], {"target_precision": -1}, "precision targets"),
        ([_record(0, 0.9, True)], {"minimum_decisions": 0}, "positive"),
    ],
)
def test_calibration_rejects_empty_invalid_digest_targets_and_minimums(
    records: list[dict[str, object]], kwargs: dict[str, object], message: str
) -> None:
    options: dict[str, object] = {
        "corpus_sha256": "a" * 64,
        "split_sha256": "b" * 64,
        "model_sha256": "c" * 64,
        "minimum_decisions": 1,
        "minimum_owners": 1,
    }
    options.update(kwargs)
    with pytest.raises(ValueError, match=message):
        calibrate_selective_thresholds(records, **options)  # type: ignore[arg-type]


def test_calibration_record_probability_boolean_owner_and_field_guards() -> None:
    for mutation, message in [
        (lambda row: row.update(extra=True), "exact declared"),
        (lambda row: row.update(owner_id=""), "owner_id"),
        (lambda row: row.update(correct=1), "boolean"),
        (lambda row: row.update(claim_probability=2), "claim_probability"),
        (lambda row: row.update(ood_score=-1), "ood_score"),
    ]:
        record = _record(0, 0.9, True)
        mutation(record)
        with pytest.raises(ValueError, match=message):
            calibrate_selective_thresholds(
                [record],
                corpus_sha256="a" * 64,
                split_sha256="b" * 64,
                model_sha256="c" * 64,
                minimum_decisions=1,
                minimum_owners=1,
            )


def test_wilson_and_calibration_verifier_defensive_states() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)
    with pytest.raises(ValueError, match="counts"):
        wilson_interval(2, 1)
    with pytest.raises(ValueError, match="confidence"):
        wilson_interval(1, 1, confidence=1)
    with pytest.raises(ValueError, match="ood_score"):
        reliability_score({**_record(0, 0.9, True), "ood_score": float("nan")})

    result = calibrate_selective_thresholds(
        [_record(0, 0.9, True)],
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        model_sha256="c" * 64,
        target_precision=1,
        target_wilson_lower=0,
        minimum_decisions=1,
        minimum_owners=1,
    )
    object.__setattr__(result, "corpus_sha256", "bad")
    object.__setattr__(result, "status", "bad")
    object.__setattr__(result, "selected_count", 0)
    errors = verify_calibration(result)
    assert any("SHA-256" in error for error in errors)
    assert "calibration status is invalid" in errors

    valid_status = copy.copy(result)
    object.__setattr__(valid_status, "corpus_sha256", "a" * 64)
    object.__setattr__(valid_status, "status", "calibrated")
    assert "calibrated result does not meet minimum_decisions" in verify_calibration(valid_status)
