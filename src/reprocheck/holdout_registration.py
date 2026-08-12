from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REGISTRATION_SCHEMA_VERSION = "reprocheck.external-holdout-registration.v1"


def register_external_holdout(protocol: Path, evaluator: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("registration output already exists; frozen registrations are immutable")
    protocol_payload = _load_protocol(protocol)
    if not evaluator.is_file():
        raise ValueError(f"evaluator does not exist: {evaluator}")
    evaluator_bytes = evaluator.read_bytes()
    registration = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "status": "registered_not_executed",
        "external_reviewers_completed": 0,
        "source_contents_inspected_after_registration": False,
        "protocol": _descriptor(protocol),
        "evaluator": {
            "filename": evaluator.name,
            "sha256": hashlib.sha256(evaluator_bytes).hexdigest(),
            "size_bytes": len(evaluator_bytes),
        },
        "source_pool_count": len(protocol_payload["source_pools"]),
        "registration_sha256": "",
    }
    registration["registration_sha256"] = _digest(registration)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(registration, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return registration


def verify_external_holdout_registration(
    registration_path: Path, protocol: Path, evaluator: Path
) -> list[str]:
    try:
        registration = _load_object(registration_path, "registration")
        _load_protocol(protocol)
    except ValueError as error:
        return [str(error)]
    errors: list[str] = []
    if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        errors.append("unsupported external holdout registration schema")
    if registration.get("status") != "registered_not_executed":
        errors.append("registration must remain registered_not_executed before evaluation")
    if registration.get("external_reviewers_completed") != 0:
        errors.append("unexecuted registration cannot claim completed external reviewers")
    if registration.get("source_contents_inspected_after_registration") is not False:
        errors.append("registration source-inspection state is not pristine")
    if registration.get("registration_sha256") != _digest(registration):
        errors.append("registration checksum does not match its payload")
    expected_protocol = registration.get("protocol")
    if expected_protocol != _descriptor(protocol):
        errors.append("registered protocol checksum or size does not match")
    if not evaluator.is_file():
        errors.append(f"registered evaluator is missing: {evaluator}")
    else:
        expected_evaluator = registration.get("evaluator")
        if expected_evaluator != _descriptor(evaluator):
            errors.append("registered evaluator checksum or size does not match")
    return errors


def _load_protocol(path: Path) -> dict[str, Any]:
    payload = _load_object(path, "holdout protocol")
    required = {
        "schema_version",
        "title",
        "research_question",
        "evaluator_version",
        "source_pools",
        "selection",
        "primary_endpoints",
        "annotation",
        "stopping_rule",
        "analysis_plan",
        "scientific_boundary",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError("holdout protocol is missing: " + ", ".join(missing))
    pools = payload.get("source_pools")
    if not isinstance(pools, list) or len(pools) < 3:
        raise ValueError("holdout protocol requires at least three source pools")
    for index, pool in enumerate(pools):
        if not isinstance(pool, dict):
            raise ValueError(f"source pool {index} must be an object")
        commit = pool.get("commit")
        if (
            not isinstance(commit, str)
            or len(commit) != 40
            or any(character not in "0123456789abcdef" for character in commit)
        ):
            raise ValueError(f"source pool {index} must pin a lowercase 40-character commit")
        if not isinstance(pool.get("repository"), str) or not str(pool["repository"]).startswith(
            "https://github.com/"
        ):
            raise ValueError(f"source pool {index} must use an explicit GitHub repository URL")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if "TBD" in encoded or "TODO" in encoded or "PLACEHOLDER" in encoded:
        raise ValueError("holdout protocol contains an unresolved placeholder")
    return payload


def _descriptor(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "filename": path.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _digest(payload: dict[str, Any]) -> str:
    canonical = dict(payload)
    canonical["registration_sha256"] = ""
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
