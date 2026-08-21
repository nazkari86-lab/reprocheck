from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .ml_contracts import canonical_contract_json


REGISTRATION_SCHEMA = "reprocheck.ml-preregistration.v1"


def _descriptor(path: Path, root: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"registered artifact is missing: {path}")
    data = path.read_bytes()
    return {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _digest(payload: dict[str, Any]) -> str:
    unsigned = {**payload, "registration_sha256": ""}
    return hashlib.sha256(canonical_contract_json(unsigned).encode()).hexdigest()


def register_ml_protocol(root: Path, artifacts: list[Path], output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("ML registration output already exists and is immutable")
    resolved_root = root.resolve()
    descriptors = []
    for path in artifacts:
        try:
            descriptors.append(_descriptor(path, resolved_root))
        except ValueError as error:
            raise ValueError(
                "registered artifacts must be files below the declared root"
            ) from error
    paths = [str(item["path"]) for item in descriptors]
    if len(set(paths)) != len(paths) or not descriptors:
        raise ValueError("registered artifacts must be non-empty and unique")
    payload: dict[str, Any] = {
        "schema_version": REGISTRATION_SCHEMA,
        "status": "registered_not_executed",
        "test_labels_opened": False,
        "prospective_sources_acquired": False,
        "artifacts": sorted(descriptors, key=lambda item: str(item["path"])),
        "registration_sha256": "",
    }
    payload["registration_sha256"] = _digest(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_contract_json(payload) + "\n", encoding="utf-8")
    return payload


def verify_ml_registration(root: Path, registration_path: Path) -> list[str]:
    try:
        payload = json.loads(registration_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"cannot load ML registration: {error}"]
    if not isinstance(payload, dict):
        return ["ML registration must be a JSON object"]
    errors: list[str] = []
    if payload.get("schema_version") != REGISTRATION_SCHEMA:
        errors.append("unsupported ML registration schema")
    if payload.get("status") != "registered_not_executed":
        errors.append("ML registration no longer has pristine status")
    if payload.get("test_labels_opened") is not False:
        errors.append("ML registration claims test labels were opened")
    if payload.get("prospective_sources_acquired") is not False:
        errors.append("prospective sources must not be acquired before model freeze")
    if payload.get("registration_sha256") != _digest(payload):
        errors.append("ML registration digest mismatch")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("ML registration artifacts must be an array")
        return errors
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "size_bytes", "sha256"}:
            errors.append("ML registration artifact descriptor is malformed")
            continue
        target = (root / str(item["path"])).resolve()
        try:
            current = _descriptor(target, root.resolve())
        except ValueError:
            errors.append(f"registered artifact is missing or unsafe: {item.get('path')}")
            continue
        if current != item:
            errors.append(f"registered artifact changed: {item['path']}")
    return errors
