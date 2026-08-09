from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .audit import run_audit
from .certificate import digest_payload
from .models import AuditReport
from .render import render_html
from .version import __version__


_MANIFEST_SCHEMA = json.loads(
    files("reprocheck")
    .joinpath("schemas/project-manifest-v1.schema.json")
    .read_text(encoding="utf-8")
)
_MANIFEST_VALIDATOR = Draft202012Validator(_MANIFEST_SCHEMA)
_RESERVED_ARTIFACT_ROLES = {
    "report",
    "notebook",
    "metrics",
    "detections",
    "predictions",
    "train",
    "test",
}


def run_project_check(
    manifest_path: Path,
    output_dir: Path,
    *,
    html: bool = False,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    root = manifest_path.resolve().parent
    completed: list[tuple[str, AuditReport]] = []

    experiments = manifest["experiments"]
    assert isinstance(experiments, list)
    seen_ids: set[str] = set()
    for raw_experiment in experiments:
        assert isinstance(raw_experiment, dict)
        experiment_id = raw_experiment["id"]
        assert isinstance(experiment_id, str)
        if experiment_id in seen_ids:
            raise ValueError(f"duplicate experiment id: {experiment_id}")
        seen_ids.add(experiment_id)

        completed.append((experiment_id, _run_experiment(root, raw_experiment)))

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for experiment_id, report in completed:
        certificate_name = f"{experiment_id}.audit.json"
        certificate_path = output_dir / certificate_name
        _write_text_atomic(
            certificate_path,
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        )
        if html:
            render_html(report, output_dir / f"{experiment_id}.audit.html")
        results.append(
            {
                "id": experiment_id,
                "status": report.status,
                "certificate": certificate_name,
                "certificate_sha256": report.certificate_sha256,
                "findings": len(report.findings),
            }
        )

    manifest_descriptor = _describe_file(manifest_path)
    payload: dict[str, Any] = {
        "schema_version": "reprocheck.batch.v1",
        "tool_version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "status": (
            "needs_review"
            if any(item["status"] == "needs_review" for item in results)
            else "passed"
        ),
        "manifest": manifest_descriptor,
        "experiments": results,
        "certificate_sha256": "",
    }
    payload["certificate_sha256"] = digest_payload(payload)
    index_path = output_dir / "batch-certificate.json"
    _write_text_atomic(
        index_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return payload


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"project manifest is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("project manifest must be a JSON object")
    errors = sorted(
        _MANIFEST_VALIDATOR.iter_errors(payload),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ValueError(f"project manifest schema violation at {location}: {error.message}")
    return payload


def _run_experiment(root: Path, experiment: dict[str, Any]) -> AuditReport:
    artifacts = experiment.get("artifacts", {})
    assert isinstance(artifacts, dict)
    reserved = sorted(_RESERVED_ARTIFACT_ROLES.intersection(artifacts))
    if reserved:
        raise ValueError(f"custom artifacts use reserved roles: {', '.join(reserved)}")
    return run_audit(
        report_path=_resolve_path(root, experiment["report"]),
        report_selector=experiment.get("report_selector"),
        notebook_path=_optional_path(root, experiment.get("notebook")),
        metrics_path=_optional_path(root, experiment.get("metrics")),
        metrics_selector=experiment.get("metrics_selector"),
        detections_path=_optional_path(root, experiment.get("detections")),
        predictions_path=_optional_path(root, experiment.get("predictions")),
        train_path=_optional_path(root, experiment.get("train")),
        test_path=_optional_path(root, experiment.get("test")),
        label_column=experiment.get("label_column"),
        group_column=experiment.get("group_column"),
        identity_columns=experiment.get("identity_columns"),
        text_column=experiment.get("text_column"),
        near_threshold=experiment.get("near_threshold", 0.9),
        positive_label=experiment.get("positive_label"),
        prediction_task=experiment.get("prediction_task", "classification"),
        average=experiment.get("average", "auto"),
        tolerance=experiment.get("tolerance", 0.005),
        extra_artifacts=[
            (role, _resolve_path(root, path)) for role, path in sorted(artifacts.items())
        ],
    )


def _optional_path(root: Path, value: object) -> Path | None:
    return _resolve_path(root, value) if value is not None else None


def _resolve_path(root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise ValueError("manifest artifact path must be a string")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"manifest artifact escapes project root: {value}")
    return path


def _describe_file(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"filename": path.name, "sha256": digest.hexdigest(), "size_bytes": size}


def _write_text_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
