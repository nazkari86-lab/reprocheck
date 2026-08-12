from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from reprocheck.witness_source_benchmark import deterministic_projection


ROOT = Path(__file__).resolve().parent


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _projection_sha256(result: dict[str, Any]) -> str:
    projection = deterministic_projection(result)
    encoded = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check the deterministic witness-source baseline")
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=ROOT / "baseline-v1.json")
    args = parser.parse_args(argv)
    result = _load(args.result)
    baseline = _load(args.baseline)
    digest = _projection_sha256(result)
    if digest != baseline.get("projection_sha256"):
        print("FAIL: witness-source deterministic projection differs from reviewed baseline")
        return 1
    summary = result.get("summary")
    if not isinstance(summary, dict):
        print("FAIL: witness-source summary is missing")
        return 1
    for field in (
        "case_count",
        "controlled_mutation_cases",
        "negative_control_cases",
        "natural_cases",
        "expected_witness_construction_rate",
        "independent_verification_rate",
        "negative_control_specificity",
        "tamper_rejection_rate",
    ):
        if summary.get(field) != baseline.get(field):
            print(f"FAIL: witness-source summary differs at {field}")
            return 1
    print(f"PASS: witness-source baseline={args.baseline.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
