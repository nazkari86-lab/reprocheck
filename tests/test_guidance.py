from pathlib import Path

from reprocheck.audit import run_audit
from reprocheck.guidance import build_audit_guide
from reprocheck.models import LeakageAudit, NotebookAudit


def test_guide_reports_exact_coverage_and_prioritized_actions(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,0\n", encoding="utf-8")

    audit = run_audit(report_path=report, predictions_path=predictions)
    guide = build_audit_guide(audit)

    assert guide["derived_from_certificate_sha256"] == audit.certificate_sha256
    assert guide["claim_coverage"] == {
        "total": 1,
        "with_evidence": 1,
        "independently_recomputed": 1,
        "matched": 0,
        "mismatched": 1,
    }
    assert {layer["id"]: layer["status"] for layer in guide["layers"]} == {
        "claims": "checked",
        "metrics": "checked",
        "splits": "not_provided",
        "notebook": "not_provided",
        "certificate": "checked",
    }
    assert [action["id"] for action in guide["actions"]] == [
        "reconcile_metrics",
        "audit_splits",
        "audit_notebook",
    ]
    assert guide["actions"][0]["priority"] == "critical"


def test_guide_is_deterministic_and_does_not_modify_certificate(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    audit = run_audit(report_path=report, predictions_path=predictions)
    certificate_before = audit.to_dict()

    first = build_audit_guide(audit)
    second = build_audit_guide(audit)

    assert first == second
    assert audit.to_dict() == certificate_before
    assert first["claim_coverage"]["matched"] == 1
    assert first["actions"][0]["id"] == "audit_splits"


def test_guide_fills_missing_evidence_action_without_a_finding(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("Accuracy: 75%", encoding="utf-8")
    audit = run_audit(report_path=report)
    audit.findings = []

    guide = build_audit_guide(audit)

    assert guide["actions"][0]["id"] == "add_metric_evidence"
    assert guide["actions"][0]["source_codes"] == []


def test_guide_recommends_preserving_a_fully_covered_certificate(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    audit = run_audit(report_path=report, predictions_path=predictions)
    audit.findings = []
    audit.leakage = LeakageAudit(
        train_rows=1,
        test_rows=1,
        identity_columns=["id"],
        exact_overlap_test_rows=0,
        normalized_overlap_test_rows=0,
        exact_overlap_rate=0.0,
        normalized_overlap_rate=0.0,
        near_overlap_test_rows=0,
        near_overlap_rate=0.0,
        train_duplicate_rows=0,
        test_duplicate_rows=0,
    )
    audit.notebook = NotebookAudit(
        filename="analysis.ipynb",
        total_cells=1,
        code_cells=1,
        executed_code_cells=1,
        has_random_seed=True,
        execution_order_monotonic=True,
        duplicate_execution_counts=[],
    )

    guide = build_audit_guide(audit)

    assert [action["id"] for action in guide["actions"]] == ["preserve_certificate"]
    assert {layer["status"] for layer in guide["layers"]} == {"checked"}
