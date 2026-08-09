from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeGuard

from jsonschema import Draft202012Validator, FormatChecker

from .models import AuditReport


_AUDIT_SCHEMA = json.loads(
    files("reprocheck")
    .joinpath("schemas/audit-report-v1.2.schema.json")
    .read_text(encoding="utf-8")
)
_AUDIT_VALIDATOR = Draft202012Validator(_AUDIT_SCHEMA, format_checker=FormatChecker())


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
