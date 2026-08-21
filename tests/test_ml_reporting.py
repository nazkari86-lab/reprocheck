from pathlib import Path

import pytest

from reprocheck.ml_calibration import calibrate_selective_thresholds
from reprocheck.ml_evaluation import evaluate_frozen_selective
from reprocheck.ml_reporting import build_frozen_scorecard, render_risk_coverage_svg


def _result():  # type: ignore[no-untyped-def]
    validation = [
        {
            "claim_id": f"v{i}",
            "owner_id": f"v-owner-{i}",
            "split": "validation",
            "claim_probability": 0.99,
            "tuple_probability": 0.99,
            "evidence_probability": 0.99,
            "completeness": 0.99,
            "rank_margin": 0.99,
            "ood_score": 0.01,
            "gate_eligible": True,
            "correct": True,
        }
        for i in range(40)
    ]
    calibration = calibrate_selective_thresholds(
        validation,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        model_sha256="c" * 64,
        minimum_decisions=20,
        minimum_owners=10,
    )
    records = [
        {
            "claim_id": f"t{i}",
            "owner_id": f"owner-{i % 30}",
            "split": "test",
            "language": ("en", "ru", "kk")[i % 3],
            "domain": "ml",
            "eligible_claim": True,
            "claim_probability": 0.99,
            "tuple_probability": 0.99,
            "evidence_probability": 0.99,
            "completeness": 0.99,
            "rank_margin": 0.99,
            "ood_score": 0.01,
            "gate_eligible": True,
            "prediction_correct": True,
            "baseline_selected": i < 50,
            "baseline_correct": i < 50,
        }
        for i in range(100)
    ]
    return evaluate_frozen_selective(records, calibration, phase="test", bootstrap_samples=10)


def test_scorecard_and_svg_are_bound_to_frozen_result(tmp_path: Path) -> None:
    result = _result()
    scorecard = build_frozen_scorecard(result)
    assert scorecard["gate_status"] == "passed"
    assert scorecard["source_result_sha256"] == result["result_sha256"]
    figure = tmp_path / "risk-coverage.svg"
    render_risk_coverage_svg(result, figure)
    assert result["result_sha256"] in figure.read_text(encoding="utf-8")

    result["system"]["precision"] = 0.5
    with pytest.raises(ValueError, match="integrity failure"):
        build_frozen_scorecard(result)
