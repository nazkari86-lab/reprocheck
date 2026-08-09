from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REGISTRATION = ROOT / "preregistration.json"
LOCK = ROOT / "preregistration.lock.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    registration = _load(REGISTRATION)
    lock = _load(LOCK)
    development = ROOT / "results" / "development-validation-v1.json"
    expected = {
        "preregistration.json": _sha256(REGISTRATION),
        "evaluate.py": _sha256(ROOT / "evaluate.py"),
        "source-manifest.json": _sha256(ROOT / "source-manifest.json"),
        "results/development-validation-v1.json": _sha256(development),
    }
    if lock.get("files") != expected:
        raise ValueError("preregistration lock hashes do not match the frozen files")

    evaluator = registration["evaluator"]
    embedded = {
        "evaluate.py": evaluator["sha256"],
        "source-manifest.json": evaluator["source_manifest_sha256"],
        "results/development-validation-v1.json": evaluator["development_result_sha256"],
    }
    for filename, digest in embedded.items():
        if expected[filename] != digest:
            raise ValueError(f"preregistration embeds a stale hash for {filename}")

    development_result = _load(development)
    thresholds = {
        method: result["threshold"] for method, result in development_result["methods"].items()
    }
    if thresholds != registration["frozen_thresholds"]:
        raise ValueError("frozen thresholds differ from the development result")
    if lock.get("test_content_downloaded_before_lock") is not False:
        raise ValueError("lock must record that test content was not downloaded")
    print(f"PASS: PAWS preregistration lock sha256={expected['preregistration.json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
