from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


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
    registration = _load(ROOT / "preregistration.json")
    manifest = _load(ROOT / "source-manifest.json")
    result_path = RESULTS / "locked-test-v1.json"
    result = _load(result_path)
    lock = _load(RESULTS / "locked-test-v1.lock.json")
    expected_files = {
        "preregistration.json": _sha256(ROOT / "preregistration.json"),
        "evaluate.py": _sha256(ROOT / "evaluate.py"),
        "source-manifest.json": _sha256(ROOT / "source-manifest.json"),
        "locked-test-v1.json": _sha256(result_path),
    }
    if lock.get("files") != expected_files:
        raise ValueError("locked-test hashes do not match the frozen study")
    if lock.get("test_runs") != 1:
        raise ValueError("locked-test metadata must record exactly one run")
    if result.get("phase") != "locked_test":
        raise ValueError("result is not marked as a locked test")
    if result["dataset"]["source_sha256"] != manifest["files"]["test"]["sha256"]:
        raise ValueError("result does not identify the preregistered test source")
    thresholds = {method: values["threshold"] for method, values in result["methods"].items()}
    if thresholds != registration["frozen_thresholds"]:
        raise ValueError("test result does not use every frozen threshold")
    print(
        "PASS: PAWS locked test "
        f"commit={lock['preregistration_commit']} sha256={expected_files['locked-test-v1.json']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
