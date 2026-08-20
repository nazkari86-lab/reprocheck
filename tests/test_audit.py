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


def test_exact_and_additional_normalized_overlap_are_reported_independently(tmp_path: Path):
    report = tmp_path / "report.md"
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    report.write_text("No metric claim.", encoding="utf-8")
    train.write_text("text,label\nNorth School,A\nCentral Park,B\n", encoding="utf-8")
    test.write_text("text,label\nNorth School,A\n  CENTRAL  PARK ,B\n", encoding="utf-8")

    result = run_audit(
        report_path=report,
        train_path=train,
        test_path=test,
        label_column="label",
        identity_columns=["text"],
    )

    assert result.leakage is not None
    assert result.leakage.normalized_only_overlap_test_rows == 1
    assert {finding["code"] for finding in result.findings} == {
        "exact_split_overlap",
        "normalized_split_overlap",
    }


def test_group_finding_uses_full_count_not_bounded_examples(tmp_path: Path):
    report = tmp_path / "report.md"
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    report.write_text("No metric claim.", encoding="utf-8")
    train.write_text(
        "id,patient,label\n"
        + "".join(f"train-{index},patient-{index},A\n" for index in range(125)),
        encoding="utf-8",
    )
    test.write_text(
        "id,patient,label\n" + "".join(f"test-{index},patient-{index},B\n" for index in range(125)),
        encoding="utf-8",
    )

    result = run_audit(
        report_path=report,
        train_path=train,
        test_path=test,
        label_column="label",
        group_column="patient",
        identity_columns=["id"],
    )

    finding = next(item for item in result.findings if item["code"] == "group_split_overlap")
    assert "125 values" in finding["message"]
    assert result.leakage is not None
    assert len(result.leakage.overlapping_groups) == 100


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


def test_selected_evidence_row_only_checks_matching_table_context(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.csv"
    report.write_text(
        "| Model | Accuracy |\n| --- | ---: |\n| baseline | 81% |\n| proposed | 92% |\n",
        encoding="utf-8",
    )
    metrics.write_text("model,accuracy\nbaseline,0.81\nproposed,0.92\n", encoding="utf-8")

    result = run_audit(
        report_path=report,
        metrics_path=metrics,
        metrics_selector="model=proposed",
    )

    assert [check.status for check in result.claims] == ["no_evidence", "supported"]
    assert result.metric_evidence["accuracy"].context == {"model": "proposed"}
    assert not any(item["code"] == "claim_metric_mismatch" for item in result.findings)


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


def test_audit_progress_reports_real_stage_boundaries(tmp_path: Path):
    report = tmp_path / "custom_report.md"
    predictions = tmp_path / "custom_predictions.csv"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    events: list[tuple[str, str, dict[str, object]]] = []

    run_audit(
        report_path=report,
        predictions_path=predictions,
        progress_callback=lambda stage, state, detail: events.append((stage, state, detail)),
    )

    assert [(stage, state) for stage, state, _ in events] == [
        ("claims", "started"),
        ("claims", "completed"),
        ("evidence", "started"),
        ("evidence", "completed"),
        ("matching", "started"),
        ("matching", "completed"),
        ("certificate", "started"),
        ("certificate", "completed"),
    ]
    assert events[1][2]["claim_count"] == 1
    assert events[3][2]["metrics"] == ["accuracy", "f1", "precision", "recall"]
    assert len(str(events[-1][2]["certificate_sha256"])) == 64


def test_run_audit_remains_available_from_public_package_api():
    import reprocheck

    assert reprocheck.run_audit is run_audit


def test_audit_rejects_incomplete_splits_negative_tolerance_and_duplicate_artifact(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("No metric claim.\n", encoding="utf-8")
    train = tmp_path / "train.csv"
    train.write_text("id,label\n1,yes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="supplied together"):
        run_audit(report_path=report, train_path=train)
    with pytest.raises(ValueError, match="non-negative"):
        run_audit(report_path=report, tolerance=-0.1)
    with pytest.raises(ValueError, match="unique"):
        run_audit(report_path=report, extra_artifacts=[("report", report)])
