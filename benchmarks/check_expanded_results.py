from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS = ROOT / "benchmarks"
OUTPUTS = ROOT / "outputs"


def main() -> int:
    failures = [*_check_frozen_hashes()]
    failures.extend(
        _compare(
            OUTPUTS / "integrity-stress.json",
            BENCHMARKS / "integrity_stress/results/frozen-v1.json",
            _identity_projection,
        )
    )
    failures.extend(
        _compare(
            OUTPUTS / "representation-robustness.json",
            BENCHMARKS / "representation_robustness/results/frozen-v1.json",
            _identity_projection,
        )
    )
    failures.extend(
        _compare(
            OUTPUTS / "real-corruptions.json",
            BENCHMARKS / "real_corruptions/results/frozen-v1.json",
            _identity_projection,
        )
    )
    failures.extend(
        _compare(
            OUTPUTS / "scalability.json",
            BENCHMARKS / "scalability/results/macos-arm64-v1.json",
            _scalability_projection,
        )
    )
    if failures:
        print("FAIL: expanded experiment regression")
        for failure in failures:
            print(failure)
        return 1
    print("PASS: expanded experiment results and deterministic projections match")
    return 0


def _check_frozen_hashes() -> list[str]:
    lock_path = BENCHMARKS / "expanded-results-v1.lock.json"
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    failures = []
    for relative, expected in payload["first_frozen_run"].items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            failures.append(f"frozen result hash mismatch: {relative}")
    return failures


def _compare(
    current_path: Path,
    frozen_path: Path,
    projection,
) -> list[str]:
    if not current_path.is_file():
        return [f"current result missing: {current_path}"]
    current = json.loads(current_path.read_text(encoding="utf-8"))
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if current.get("tool_version") != __version__:
        return [
            f"current result version mismatch: {current_path.name} "
            f"({current.get('tool_version')} != {__version__})"
        ]
    if projection(current) != projection(frozen):
        return [f"result projection mismatch: {current_path.name}"]
    return []


def _identity_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "tool_version"}


def _scalability_projection(payload: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for case in payload["cases"]:
        cases.append(
            {
                key: value
                for key, value in case.items()
                if key not in {"median_wall_ms", "min_wall_ms", "max_wall_ms"}
            }
        )
        if not all(case[key] > 0 for key in ("median_wall_ms", "min_wall_ms", "max_wall_ms")):
            cases[-1]["invalid_timing"] = True
    return {
        "schema": payload["schema"],
        "cases": cases,
        "summary": payload["summary"],
        "scientific_boundary": payload["scientific_boundary"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
