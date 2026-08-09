from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re

from .certificate import seal_report
from .claims import check_claims, extract_claims
from .documents import extract_document_text
from .detection import detection_evidence
from .evidence import load_metric_evidence, metric_evidence_from_predictions
from .leakage import audit_csv_splits
from .models import AuditReport, MetricObservation
from .notebook import audit_notebook
from .provenance import describe_artifact
from .version import __version__


def run_audit(
    *,
    report_path: Path,
    report_selector: str | None = None,
    notebook_path: Path | None = None,
    metrics_path: Path | None = None,
    metrics_selector: str | None = None,
    detections_path: Path | None = None,
    predictions_path: Path | None = None,
    train_path: Path | None = None,
    test_path: Path | None = None,
    label_column: str | None = None,
    group_column: str | None = None,
    identity_columns: list[str] | None = None,
    text_column: str | None = None,
    near_threshold: float = 0.8,
    near_method: str = "hybrid_lexical_v1",
    positive_label: str | None = None,
    average: str = "auto",
    prediction_task: str = "classification",
    tolerance: float = 0.005,
    extra_artifacts: list[tuple[str, Path]] | None = None,
) -> AuditReport:
    if (train_path is None) != (test_path is None):
        raise ValueError("train and test files must be supplied together")
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")

    artifacts = [describe_artifact(report_path, "report")]
    for role, path in extra_artifacts or []:
        if role in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.-]+", role):
            raise ValueError(f"invalid artifact role: {role}")
        artifacts.append(describe_artifact(path, role))
    text = extract_document_text(report_path, selector=report_selector)
    claims = extract_claims(text)
    metric_evidence = {}
    evidence_conflicts: list[dict[str, object]] = []

    if metrics_path:
        artifacts.append(describe_artifact(metrics_path, "metrics"))
        _merge_metric_evidence(
            metric_evidence,
            load_metric_evidence(metrics_path, selector=metrics_selector),
            tolerance=tolerance,
            conflicts=evidence_conflicts,
        )
    if detections_path:
        artifacts.append(describe_artifact(detections_path, "detections"))
        _merge_metric_evidence(
            metric_evidence,
            detection_evidence(detections_path),
            tolerance=tolerance,
            conflicts=evidence_conflicts,
        )
    if predictions_path:
        artifacts.append(describe_artifact(predictions_path, "predictions"))
        _merge_metric_evidence(
            metric_evidence,
            metric_evidence_from_predictions(
                predictions_path,
                positive_label=positive_label,
                average=average,
                task=prediction_task,
            ),
            tolerance=tolerance,
            conflicts=evidence_conflicts,
        )
    observed = {name: evidence.value for name, evidence in metric_evidence.items()}

    resolved_notebook_path = notebook_path
    if resolved_notebook_path is None and report_path.suffix.lower() == ".ipynb":
        resolved_notebook_path = report_path
    notebook = None
    if resolved_notebook_path:
        if resolved_notebook_path != report_path:
            artifacts.append(describe_artifact(resolved_notebook_path, "notebook"))
        notebook = audit_notebook(resolved_notebook_path)

    leakage = None
    if train_path and test_path:
        artifacts.extend(
            [describe_artifact(train_path, "train"), describe_artifact(test_path, "test")]
        )
        leakage = audit_csv_splits(
            train_path,
            test_path,
            label_column=label_column,
            group_column=group_column,
            identity_columns=identity_columns,
            text_column=text_column,
            near_threshold=near_threshold,
            near_method=near_method,
        )

    artifact_identities = [(item.role, item.filename) for item in artifacts]
    if len(set(artifact_identities)) != len(artifact_identities):
        raise ValueError("artifact roles and filenames must be unique")

    checks = check_claims(
        claims,
        observed,
        tolerance,
        evidence_levels={name: item.evidence_level for name, item in metric_evidence.items()},
        evidence_contexts={name: item.context for name, item in metric_evidence.items()},
    )
    findings: list[dict[str, object]] = []
    findings.extend(evidence_conflicts)
    if not claims and metric_evidence:
        findings.append(
            {
                "severity": "medium",
                "code": "no_metric_claims_detected",
                "message": "Metric evidence was supplied, but no supported metric claim was found.",
            }
        )
    elif not claims and not any((resolved_notebook_path, train_path, test_path)):
        findings.append(
            {
                "severity": "medium",
                "code": "nothing_auditable_detected",
                "message": "No metric claims, split pair, or notebook were supplied for audit.",
            }
        )
    if notebook:
        findings.extend(notebook.findings)
    for check in checks:
        if check.status == "mismatch":
            findings.append(
                {
                    "severity": "high",
                    "code": "claim_metric_mismatch",
                    "message": (
                        f"Claimed {check.claim.metric}={check.claim.value:.4f}, "
                        f"observed {check.observed:.4f}."
                    ),
                    "line": check.claim.line,
                }
            )
        elif check.status == "no_evidence":
            findings.append(
                {
                    "severity": "medium",
                    "code": "claim_without_evidence",
                    "message": f"No metric evidence for {check.claim.metric} claim.",
                    "line": check.claim.line,
                }
            )

    if leakage:
        if leakage.exact_overlap_test_rows:
            findings.append(
                {
                    "severity": "high",
                    "code": "exact_split_overlap",
                    "message": (
                        f"{leakage.exact_overlap_test_rows}/{leakage.test_rows} test rows "
                        "also occur in train."
                    ),
                }
            )
        if leakage.normalized_only_overlap_test_rows:
            findings.append(
                {
                    "severity": "high",
                    "code": "normalized_split_overlap",
                    "message": (
                        f"{leakage.normalized_only_overlap_test_rows}/{leakage.test_rows} "
                        "additional test rows occur in train only after normalization."
                    ),
                }
            )
        if leakage.overlapping_group_count:
            findings.append(
                {
                    "severity": "high",
                    "code": "group_split_overlap",
                    "message": (
                        f"{leakage.overlapping_group_count} values of {group_column} occur in both splits."
                    ),
                }
            )
        if leakage.near_overlap_test_rows:
            findings.append(
                {
                    "severity": "medium",
                    "code": "near_text_split_overlap",
                    "message": (
                        f"{leakage.near_overlap_test_rows}/{leakage.test_rows} test rows have "
                        f"text similarity >= {near_threshold:.2f} with train."
                    ),
                }
            )

    result = AuditReport(
        schema_version="1.2",
        tool_version=__version__,
        created_at=datetime.now(UTC).isoformat(),
        status="needs_review" if findings else "passed",
        artifacts=artifacts,
        claims=checks,
        observed_metrics=observed,
        metric_evidence=metric_evidence,
        leakage=leakage,
        notebook=notebook,
        findings=findings,
        parameters={
            "tolerance": tolerance,
            "report_selector": report_selector,
            "metrics_selector": metrics_selector,
            "label_column": label_column,
            "group_column": group_column,
            "identity_columns": identity_columns,
            "text_column": text_column,
            "near_threshold": near_threshold,
            "near_method": near_method,
            "positive_label": positive_label,
            "average": average,
            "prediction_task": prediction_task,
            "extra_artifacts": [
                {"role": role, "filename": path.name} for role, path in extra_artifacts or []
            ],
        },
    )
    return seal_report(result)


def _merge_metric_evidence(
    existing: dict[str, MetricObservation],
    incoming: dict[str, MetricObservation],
    *,
    tolerance: float,
    conflicts: list[dict[str, object]],
) -> None:
    priority = {"reported": 0, "recomputed": 1}
    for metric, observation in incoming.items():
        previous = existing.get(metric)
        if previous is not None and abs(previous.value - observation.value) > tolerance:
            conflicts.append(
                {
                    "severity": "high",
                    "code": "metric_evidence_conflict",
                    "message": (
                        f"Conflicting {metric} evidence: {previous.value:.8g} from "
                        f"{previous.source} versus {observation.value:.8g} from "
                        f"{observation.source}."
                    ),
                    "metric": metric,
                    "sources": [previous.source, observation.source],
                    "values": [previous.value, observation.value],
                }
            )
        if (
            previous is None
            or priority[observation.evidence_level] >= priority[previous.evidence_level]
        ):
            existing[metric] = observation
