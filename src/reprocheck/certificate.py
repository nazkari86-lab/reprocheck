from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeGuard

from jsonschema import Draft202012Validator, FormatChecker

from .evidence_graph import verify_evidence_graph
from .models import AuditReport


_AUDIT_SCHEMA = json.loads(
    files("reprocheck")
    .joinpath("schemas/audit-report-v1.2.schema.json")
    .read_text(encoding="utf-8")
)
_AUDIT_VALIDATOR = Draft202012Validator(_AUDIT_SCHEMA, format_checker=FormatChecker())
_BATCH_SCHEMA = json.loads(
    files("reprocheck")
    .joinpath("schemas/batch-certificate-v1.schema.json")
    .read_text(encoding="utf-8")
)
_BATCH_VALIDATOR = Draft202012Validator(_BATCH_SCHEMA, format_checker=FormatChecker())
_PROJECT_SCHEMA = json.loads(
    files("reprocheck")
    .joinpath("schemas/project-manifest-v1.schema.json")
    .read_text(encoding="utf-8")
)
_PROJECT_VALIDATOR = Draft202012Validator(_PROJECT_SCHEMA)


def seal_report(report: AuditReport) -> AuditReport:
    report.certificate_sha256 = digest_payload(report.to_dict())
    return report


def digest_payload(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise ValueError("certificate payload must be a JSON object")
    canonical = dict(payload)
    canonical.pop("created_at", None)
    canonical["certificate_sha256"] = ""
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_certificate_file(path: Path, artifact_dir: Path | None = None) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"certificate cannot be read: {error}"]
    if not isinstance(payload, dict):
        return ["certificate payload must be a JSON object"]
    if payload.get("schema_version") == "reprocheck.batch.v1":
        return _verify_batch_certificate(payload, path, artifact_dir)
    expected = payload.get("certificate_sha256", "")
    errors: list[str] = []
    try:
        actual = digest_payload(payload)
    except (TypeError, ValueError) as error:
        return [f"certificate payload is not canonicalizable: {error}"]
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        errors.append("certificate checksum is missing or malformed")
    elif expected != actual:
        errors.append("certificate checksum does not match its payload")

    schema_errors = sorted(
        _AUDIT_VALIDATOR.iter_errors(payload),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
    )
    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"certificate schema violation at {location}: {error.message}")

    if not schema_errors and payload.get("evidence_graph") is not None:
        errors.extend(verify_evidence_graph(payload["evidence_graph"]))

    if artifact_dir:
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append("certificate artifacts must be an array")
            return errors
        root = artifact_dir.resolve()
        seen: set[tuple[str, str]] = set()
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"artifact descriptor {index} must be an object")
                continue
            filename = artifact.get("filename")
            role = artifact.get("role")
            digest = artifact.get("sha256")
            size = artifact.get("size_bytes")
            if not _safe_component(filename):
                errors.append(f"artifact filename is unsafe: {filename!r}")
                continue
            if not _safe_component(role):
                errors.append(f"artifact role is unsafe: {role!r}")
                continue
            identity = (role, filename)
            if identity in seen:
                errors.append(f"duplicate artifact descriptor: {role}/{filename}")
                continue
            seen.add(identity)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                errors.append(f"artifact checksum is malformed: {filename}")
                continue
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                errors.append(f"artifact size is malformed: {filename}")
                continue
            candidates = [root / filename, root / role / filename]
            sources = [candidate for candidate in candidates if candidate.is_file()]
            if not sources:
                errors.append(f"artifact is missing: {filename}")
                continue
            if not any(
                source.stat().st_size == size and _sha256(source) == digest for source in sources
            ):
                errors.append(f"artifact checksum or size mismatch: {filename}")
    return errors


def _verify_batch_certificate(
    payload: dict[str, Any],
    path: Path,
    artifact_dir: Path | None,
) -> list[str]:
    errors = _verify_payload_digest(payload)
    schema_errors = sorted(
        _BATCH_VALIDATOR.iter_errors(payload),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
    )
    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"batch certificate schema violation at {location}: {error.message}")
    if schema_errors:
        return errors

    manifest = payload["manifest"]
    assert isinstance(manifest, dict)
    manifest_payload: dict[str, Any] | None = None
    if artifact_dir:
        manifest_path = artifact_dir.resolve() / manifest["filename"]
        if not manifest_path.is_file():
            errors.append(f"batch manifest is missing: {manifest['filename']}")
        elif (
            manifest_path.stat().st_size != manifest["size_bytes"]
            or _sha256(manifest_path) != manifest["sha256"]
        ):
            errors.append(f"batch manifest checksum or size mismatch: {manifest['filename']}")
        else:
            try:
                loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                errors.append(f"batch manifest cannot be read: {error}")
            else:
                if not isinstance(loaded_manifest, dict):
                    errors.append("batch manifest must be a JSON object")
                else:
                    manifest_errors = sorted(
                        _PROJECT_VALIDATOR.iter_errors(loaded_manifest),
                        key=lambda error: (
                            tuple(str(part) for part in error.absolute_path),
                            error.message,
                        ),
                    )
                    for error in manifest_errors:
                        location = ".".join(str(part) for part in error.absolute_path) or "$"
                        errors.append(
                            f"batch manifest schema violation at {location}: {error.message}"
                        )
                    if not manifest_errors:
                        manifest_payload = loaded_manifest

    manifest_experiments: dict[str, dict[str, Any]] = {}
    if manifest_payload:
        raw_experiments = manifest_payload["experiments"]
        assert isinstance(raw_experiments, list)
        for raw_experiment in raw_experiments:
            assert isinstance(raw_experiment, dict)
            raw_id = raw_experiment["id"]
            assert isinstance(raw_id, str)
            if raw_id in manifest_experiments:
                errors.append(f"duplicate project manifest experiment id: {raw_id}")
            manifest_experiments[raw_id] = raw_experiment

    expected_status = "passed"
    seen_ids: set[str] = set()
    seen_certificates: set[str] = set()
    experiments = payload["experiments"]
    assert isinstance(experiments, list)
    for item in experiments:
        assert isinstance(item, dict)
        experiment_id = item["id"]
        certificate_name = item["certificate"]
        if experiment_id in seen_ids:
            errors.append(f"duplicate batch experiment id: {experiment_id}")
        if certificate_name in seen_certificates:
            errors.append(f"duplicate child certificate: {certificate_name}")
        seen_ids.add(experiment_id)
        seen_certificates.add(certificate_name)

        child_path = path.resolve().parent / certificate_name
        if not child_path.is_file():
            errors.append(f"child certificate is missing: {certificate_name}")
            continue
        try:
            child = json.loads(child_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(f"child certificate cannot be read ({certificate_name}): {error}")
            continue
        if not isinstance(child, dict):
            errors.append(f"child certificate must be a JSON object: {certificate_name}")
            continue
        if child.get("certificate_sha256") != item["certificate_sha256"]:
            errors.append(f"child certificate digest mismatch: {certificate_name}")
        if child.get("status") != item["status"]:
            errors.append(f"child certificate status mismatch: {certificate_name}")
        findings = child.get("findings")
        if not isinstance(findings, list) or len(findings) != item["findings"]:
            errors.append(f"child certificate finding count mismatch: {certificate_name}")
        child_errors = verify_certificate_file(child_path)
        errors.extend(f"{certificate_name}: {error}" for error in child_errors)
        if artifact_dir and experiment_id in manifest_experiments:
            errors.extend(
                _verify_manifest_artifacts(
                    child,
                    manifest_experiments[experiment_id],
                    artifact_dir.resolve(),
                    certificate_name,
                )
            )
        elif artifact_dir and manifest_payload:
            errors.append(f"experiment is missing from batch manifest: {experiment_id}")
        if item["status"] == "needs_review":
            expected_status = "needs_review"
    if payload["status"] != expected_status:
        errors.append("batch status does not match child certificate statuses")
    return errors


def _verify_manifest_artifacts(
    child: dict[str, Any],
    experiment: dict[str, Any],
    root: Path,
    certificate_name: str,
) -> list[str]:
    path_by_role: dict[str, object] = {"report": experiment["report"]}
    for role in ("metrics", "detections", "predictions", "train", "test"):
        if role in experiment:
            path_by_role[role] = experiment[role]
    notebook = experiment.get("notebook")
    if notebook is not None and notebook != experiment["report"]:
        path_by_role["notebook"] = notebook
    custom = experiment.get("artifacts", {})
    assert isinstance(custom, dict)
    path_by_role.update(custom)

    artifacts = child.get("artifacts")
    if not isinstance(artifacts, list):
        return [f"{certificate_name}: certificate artifacts must be an array"]
    errors: list[str] = []
    seen_roles: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append(f"{certificate_name}: artifact descriptor must be an object")
            continue
        role = artifact.get("role")
        if not isinstance(role, str) or role not in path_by_role:
            errors.append(f"{certificate_name}: artifact role is absent from manifest: {role!r}")
            continue
        if role in seen_roles:
            errors.append(f"{certificate_name}: duplicate artifact role: {role}")
            continue
        seen_roles.add(role)
        source = _safe_project_path(root, path_by_role[role])
        if source is None:
            errors.append(f"{certificate_name}: unsafe artifact path for role {role}")
            continue
        if not source.is_file():
            errors.append(f"{certificate_name}: artifact is missing: {source.name}")
            continue
        if artifact.get("filename") != source.name:
            errors.append(f"{certificate_name}: artifact filename mismatch for role {role}")
            continue
        if artifact.get("size_bytes") != source.stat().st_size or artifact.get("sha256") != _sha256(
            source
        ):
            errors.append(f"{certificate_name}: artifact checksum or size mismatch: {source.name}")
    missing_roles = sorted(set(path_by_role).difference(seen_roles))
    for role in missing_roles:
        errors.append(f"{certificate_name}: manifest artifact is absent from certificate: {role}")
    return errors


def _safe_project_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    path = (root / value).resolve()
    return path if path.is_relative_to(root) else None


def _verify_payload_digest(payload: dict[str, Any]) -> list[str]:
    expected = payload.get("certificate_sha256", "")
    try:
        actual = digest_payload(payload)
    except (TypeError, ValueError) as error:
        return [f"certificate payload is not canonicalizable: {error}"]
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        return ["certificate checksum is missing or malformed"]
    if expected != actual:
        return ["certificate checksum does not match its payload"]
    return []


def _safe_component(value: object) -> TypeGuard[str]:
    if not isinstance(value, str) or not value or value in {".", ".."}:
        return False
    return Path(value).name == value and "/" not in value and "\\" not in value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
