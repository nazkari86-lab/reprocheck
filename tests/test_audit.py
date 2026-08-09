from pathlib import Path

import pytest

from reprocheck.audit import run_audit


def test_end_to_end_audit_reports_mismatch_and_leakage(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,0\n", encoding="utf-8")
    train.write_text("id,label\n1,A\n", encoding="utf-8")
    test.write_text("id,label\n1,A\n", encoding="utf-8")

    result = run_audit(
        report_path=report,
        predictions_path=predictions,
        train_path=train,
        test_path=test,
        label_column="label",
    )
    assert result.status == "needs_review"
    assert {finding["code"] for finding in result.findings} == {
        "claim_metric_mismatch",
        "exact_split_overlap",
    }
    assert len(result.artifacts) == 4


def test_json_claim_matches_selected_wide_csv_row(tmp_path: Path):
    report = tmp_path / "claims.json"
    metrics = tmp_path / "metrics.csv"
    report.write_text(
        '{"claims":[{"claim":"Hard Dice 0.9036 and hard IoU 0.8242"}]}',
        encoding="utf-8",
    )
    metrics.write_text(
        "experiment,hard_dice,hard_iou\ncompact,0.9036145,0.824176\n",
        encoding="utf-8",
    )
    result = run_audit(
        report_path=report,
        report_selector="claims.0.claim",
        metrics_path=metrics,
        metrics_selector="experiment=compact",
        tolerance=0.0001,
    )
    assert result.status == "passed"
    assert [check.status for check in result.claims] == ["supported", "supported"]


def test_conflicting_reported_and_recomputed_metrics_need_review(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    predictions = tmp_path / "predictions.csv"
    report.write_text("Accuracy: 50%", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}', encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,0\n", encoding="utf-8")

    result = run_audit(
        report_path=report,
        metrics_path=metrics,
        predictions_path=predictions,
    )
    assert result.status == "needs_review"
    assert result.claims[0].status == "verified"
    assert result.observed_metrics["accuracy"] == 0.5
    assert {finding["code"] for finding in result.findings} == {"metric_evidence_conflict"}


def test_metric_evidence_without_claim_is_not_a_pass(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    report.write_text("No numerical result is stated.", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}', encoding="utf-8")

    result = run_audit(report_path=report, metrics_path=metrics)
    assert result.status == "needs_review"
    assert result.findings[0]["code"] == "no_metric_claims_detected"


def test_additional_research_artifact_is_certified(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    model = tmp_path / "model.bin"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    model.write_bytes(b"frozen-model")

    result = run_audit(
        report_path=report,
        predictions_path=predictions,
        extra_artifacts=[("model", model)],
    )
    assert result.status == "passed"
    assert [(item.role, item.filename) for item in result.artifacts] == [
        ("report", "report.md"),
        ("model", "model.bin"),
        ("predictions", "predictions.csv"),
    ]

    with pytest.raises(ValueError, match="invalid artifact role"):
        run_audit(
            report_path=report,
            predictions_path=predictions,
            extra_artifacts=[("../model", model)],
        )
    with pytest.raises(ValueError, match="invalid artifact role"):
        run_audit(
            report_path=report,
            predictions_path=predictions,
            extra_artifacts=[("..", model)],
        )


def test_regression_claims_are_independently_verified(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    report.write_text("RMSE: 0.816497\nMAE: 0.666667\nR2: 0", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n2,3\n3,2\n", encoding="utf-8")
    result = run_audit(
        report_path=report,
        predictions_path=predictions,
        prediction_task="regression",
        tolerance=0.000001,
    )
    assert result.status == "passed"
    assert [check.status for check in result.claims] == [
        "verified",
        "verified",
        "verified",
    ]


def test_run_audit_remains_available_from_public_package_api():
    import reprocheck

    assert reprocheck.run_audit is run_audit
