from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "reprocheck.evidence-trial-operator-tooling-status.v1"
REQUIRED_ROLES = {"source_only_curator", "blinded_reviewer", "disagreement_adjudicator"}


def _descriptor(path: Path, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "filename": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def verify(status_path: Path) -> list[str]:
    root = status_path.parent
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA:
        return ["unsupported operator tooling status schema"]
    errors: list[str] = []
    for name in ("registration", "curation_packet"):
        expected = payload.get(name)
        if not isinstance(expected, dict) or not isinstance(expected.get("filename"), str):
            errors.append(f"{name} descriptor is missing")
            continue
        path = root / expected["filename"]
        if not path.is_file() or _descriptor(path, root) != expected:
            errors.append(f"{name} descriptor does not match current bytes")
    tools = payload.get("tools")
    if not isinstance(tools, list):
        return errors + ["tool descriptors are missing"]
    roles = {item.get("role") for item in tools if isinstance(item, dict)}
    if roles != REQUIRED_ROLES or len(tools) != len(REQUIRED_ROLES):
        errors.append("operator tool roles must be unique and complete")
    for item in tools:
        if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
            errors.append("operator tool descriptor is invalid")
            continue
        expected = {key: item[key] for key in ("filename", "sha256", "size_bytes")}
        path = root / item["filename"]
        if not path.is_file() or _descriptor(path, root) != expected:
            errors.append(f"operator tool bytes do not match: {item['filename']}")
        if item.get("loopback_only") is not True:
            errors.append(f"operator tool is not loopback-only: {item['filename']}")
        if item.get("server_persists_labels") is not False:
            errors.append(f"operator tool may persist labels: {item['filename']}")
        if item.get("evaluator_outputs_exposed") is not False:
            errors.append(f"operator tool may expose evaluator outputs: {item['filename']}")
    if payload.get("independent_human_status") != "pending":
        errors.append(
            "independent human status must remain pending until real signed handoffs exist"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify post-registration operator tools")
    parser.add_argument(
        "--status", type=Path, default=Path(__file__).with_name("operator-tooling-status.json")
    )
    args = parser.parse_args(argv)
    errors = verify(args.status)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: operator tools match their hash-bound status and human work remains pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
