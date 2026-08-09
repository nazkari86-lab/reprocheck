from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .audit import run_audit
from .certificate import digest_payload
from .version import __version__


def run_controlled_benchmark(output: Path | None = None) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-benchmark-") as directory:
        root = Path(directory)
        cases.extend(
            [
                _clean_case(root / "clean"),
                _metric_mismatch_case(root / "metric"),
                _split_case(
                    root / "exact",
                    "North school",
                    "North school",
                    "exact_split_overlap",
                ),
                _split_case(
                    root / "normalized",
                    "Central Park",
                    "  CENTRAL   PARK ",
                    "normalized_split_overlap",
                ),
                _group_case(root / "group"),
                _near_overlap_case(root / "near"),
                _notebook_case(root / "notebook"),
                _evidence_conflict_case(root / "conflict"),
                _no_claim_case(root / "no-claim"),
                _detection_mismatch_case(root / "detection"),
                _reported_support_case(root / "supported"),
                _regression_case(root / "regression"),
            ]
        )
        rejection_cases = [
            _duplicate_metric_rejection(root / "reject-metric"),
            _invalid_detection_rejection(root / "reject-detection"),
            _empty_split_rejection(root / "reject-split"),
        ]

    expected_total = sum(len(case["expected_codes"]) for case in cases)
    detected_total = sum(
        len(set(case["expected_codes"]) & set(case["actual_codes"])) for case in cases
    )
    actual_total = sum(len(case["actual_codes"]) for case in cases)
    unexpected_total = sum(
        len(set(case["actual_codes"]) - set(case["expected_codes"])) for case in cases
    )
    result = {
        "schema_version": "1.1",
        "tool_version": __version__,
        "cases": cases,
        "rejection_cases": rejection_cases,
        "case_pass_rate": sum(case["passed"] for case in cases) / len(cases),
        "expected_finding_recall": detected_total / expected_total if expected_total else 1.0,
        "expected_finding_precision": detected_total / actual_total if actual_total else 1.0,
        "unexpected_findings": unexpected_total,
        "certificate_integrity_rate": sum(case["certificate_valid"] for case in cases) / len(cases),
        "certificate_tamper_detection_rate": sum(
            case["certificate_tamper_detected"] for case in cases
        )
        / len(cases),
        "invalid_input_rejection_rate": sum(case["rejected"] for case in rejection_cases)
        / len(rejection_cases),
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _clean_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    predictions = _write(root / "predictions.csv", "y_true,y_pred\n0,0\n1,1\n")
    train = _write(root / "train.csv", "text,label\nNorth,A\n")
    test = _write(root / "test.csv", "text,label\nSouth,B\n")
    result = run_audit(
        report_path=report,
        predictions_path=predictions,
        train_path=train,
        test_path=test,
        label_column="label",
        identity_columns=["text"],
    )
    return _case_result("clean", [], result, expected_claim_statuses=["verified"])


def _metric_mismatch_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    predictions = _write(root / "predictions.csv", "y_true,y_pred\n0,0\n1,0\n")
    result = run_audit(report_path=report, predictions_path=predictions)
    return _case_result(
        "metric_mismatch",
        ["claim_metric_mismatch"],
        result,
        expected_claim_statuses=["mismatch"],
    )


def _split_case(root: Path, train_text: str, test_text: str, expected: str) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    metrics = _write(root / "metrics.json", '{"accuracy": 1.0}')
    train = _write(root / "train.csv", f"text,label\n{train_text},A\n")
    test = _write(root / "test.csv", f"text,label\n{test_text},A\n")
    result = run_audit(
        report_path=report,
        metrics_path=metrics,
        train_path=train,
        test_path=test,
        label_column="label",
        identity_columns=["text"],
    )
    return _case_result(expected.removesuffix("_overlap"), [expected], result)


def _group_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    metrics = _write(root / "metrics.json", '{"accuracy": 1.0}')
    train = _write(root / "train.csv", "source,text,label\n Patient-1 ,North,A\n")
    test = _write(root / "test.csv", "source,text,label\npatient-1,South,B\n")
    result = run_audit(
        report_path=report,
        metrics_path=metrics,
        train_path=train,
        test_path=test,
        label_column="label",
        group_column="source",
        identity_columns=["text"],
    )
    return _case_result("group_overlap", ["group_split_overlap"], result)


def _near_overlap_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    metrics = _write(root / "metrics.json", '{"accuracy": 1.0}')
    train = _write(root / "train.csv", "id,text,label\n1,red brick school in almaty,A\n")
    test = _write(
        root / "test.csv",
        "id,text,label\n2,red brick school located in almaty,A\n",
    )
    result = run_audit(
        report_path=report,
        metrics_path=metrics,
        train_path=train,
        test_path=test,
        label_column="label",
        identity_columns=["id"],
        text_column="text",
        near_threshold=0.8,
    )
    return _case_result("near_text_overlap", ["near_text_split_overlap"], result)


def _notebook_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    metrics = _write(root / "metrics.json", '{"accuracy": 1.0}')
    notebook = root / "experiment.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "nbformat": 4,
                "nbformat_minor": 5,
                "metadata": {},
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 2,
                        "metadata": {},
                        "outputs": [],
                        "source": "X = scaler.fit_transform(data)\n",
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "metadata": {},
                        "outputs": [],
                        "source": (
                            "X_train, X_test = train_test_split(X)\nmodel.fit(X_test, y_test)\n"
                        ),
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    result = run_audit(report_path=report, metrics_path=metrics, notebook_path=notebook)
    expected = [
        "non_monotonic_notebook_execution",
        "preprocessing_before_split",
        "fit_on_test_data",
        "random_seed_not_detected",
    ]
    return _case_result("notebook_pipeline", expected, result)


def _evidence_conflict_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 50%")
    metrics = _write(root / "metrics.json", '{"accuracy": 0.9}')
    predictions = _write(root / "predictions.csv", "y_true,y_pred\n0,0\n1,0\n")
    result = run_audit(
        report_path=report,
        metrics_path=metrics,
        predictions_path=predictions,
    )
    return _case_result(
        "evidence_conflict",
        ["metric_evidence_conflict"],
        result,
        expected_claim_statuses=["verified"],
    )


def _no_claim_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Results are discussed without a numerical metric.")
    metrics = _write(root / "metrics.json", '{"accuracy": 0.9}')
    result = run_audit(report_path=report, metrics_path=metrics)
    return _case_result("missing_claim", ["no_metric_claims_detected"], result)


def _detection_mismatch_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "mAP50: 100%")
    detections = _write(
        root / "detections.json",
        json.dumps(
            {
                "images": [
                    {
                        "id": "one",
                        "ground_truth": [{"class_id": 0, "bbox": [0, 0, 10, 10]}],
                        "predictions": [],
                    }
                ]
            }
        ),
    )
    result = run_audit(report_path=report, detections_path=detections)
    return _case_result(
        "detection_mismatch",
        ["claim_metric_mismatch"],
        result,
        expected_claim_statuses=["mismatch"],
    )


def _reported_support_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 90%")
    metrics = _write(root / "metrics.json", '{"accuracy": 0.9}')
    result = run_audit(report_path=report, metrics_path=metrics)
    return _case_result(
        "reported_metric_support",
        [],
        result,
        expected_claim_statuses=["supported"],
    )


def _regression_case(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "RMSE: 0.816497\nMAE: 0.666667\nR2: 0")
    predictions = _write(root / "predictions.csv", "y_true,y_pred\n1,1\n2,3\n3,2\n")
    result = run_audit(
        report_path=report,
        predictions_path=predictions,
        prediction_task="regression",
        tolerance=0.000001,
    )
    return _case_result(
        "regression_recomputation",
        [],
        result,
        expected_claim_statuses=["verified", "verified", "verified"],
    )


def _case_result(
    name: str,
    expected: list[str],
    report,
    *,
    expected_claim_statuses: list[str] | None = None,
) -> dict[str, Any]:
    actual = [finding["code"] for finding in report.findings]
    actual_claim_statuses = [check.status for check in report.claims]
    tampered = report.to_dict()
    tampered["status"] = "passed" if report.status == "needs_review" else "needs_review"
    return {
        "name": name,
        "expected_codes": expected,
        "actual_codes": actual,
        "expected_claim_statuses": expected_claim_statuses,
        "actual_claim_statuses": actual_claim_statuses,
        "passed": set(expected) == set(actual)
        and (expected_claim_statuses is None or expected_claim_statuses == actual_claim_statuses),
        "certificate_valid": digest_payload(report.to_dict()) == report.certificate_sha256,
        "certificate_tamper_detected": digest_payload(tampered) != report.certificate_sha256,
    }


def _duplicate_metric_rejection(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "F1: 80%")
    metrics = _write(root / "metrics.json", '{"f1": 0.8, "f1_score": 0.8}')
    return _rejection_result(
        "duplicate_normalized_metric",
        lambda: run_audit(report_path=report, metrics_path=metrics),
        "duplicate metric",
    )


def _invalid_detection_rejection(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "mAP50: 80%")
    detections = _write(
        root / "detections.json",
        json.dumps(
            {
                "images": [
                    {
                        "id": "one",
                        "ground_truth": [{"class_id": 0, "bbox": [10, 0, 0, 10]}],
                        "predictions": [],
                    }
                ]
            }
        ),
    )
    return _rejection_result(
        "invalid_detection_bbox",
        lambda: run_audit(report_path=report, detections_path=detections),
        "positive width",
    )


def _empty_split_rejection(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    report = _write(root / "report.md", "Accuracy: 100%")
    metrics = _write(root / "metrics.json", '{"accuracy": 1.0}')
    train = _write(root / "train.csv", "id,label\n")
    test = _write(root / "test.csv", "id,label\n1,A\n")
    return _rejection_result(
        "empty_train_split",
        lambda: run_audit(
            report_path=report,
            metrics_path=metrics,
            train_path=train,
            test_path=test,
            label_column="label",
        ),
        "split is empty",
    )


def _rejection_result(
    name: str, operation: Callable[[], object], expected_message: str
) -> dict[str, Any]:
    try:
        operation()
    except ValueError as error:
        message = str(error)
        return {
            "name": name,
            "expected_message": expected_message,
            "actual_message": message,
            "rejected": expected_message in message,
        }
    return {
        "name": name,
        "expected_message": expected_message,
        "actual_message": None,
        "rejected": False,
    }


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
