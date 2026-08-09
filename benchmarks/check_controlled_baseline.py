from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_RESULT = ROOT.parent / "outputs" / "benchmark.json"
DEFAULT_BASELINE = ROOT / "baseline-v0.9.1.json"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def deterministic_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_version": result["tool_version"],
        "behavioral_cases": len(result["cases"]),
        "rejection_cases": len(result["rejection_cases"]),
        "case_pass_rate": result["case_pass_rate"],
        "expected_finding_recall": result["expected_finding_recall"],
        "expected_finding_precision": result["expected_finding_precision"],
        "unexpected_findings": result["unexpected_findings"],
        "certificate_integrity_rate": result["certificate_integrity_rate"],
        "certificate_tamper_detection_rate": result["certificate_tamper_detection_rate"],
        "invalid_input_rejection_rate": result["invalid_input_rejection_rate"],
        "scope": (
            "controlled synthetic defects; public-artifact extraction and 130 real-file "
            "mutations are reported separately in real_artifacts/baseline-v6.json"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check the controlled benchmark baseline")
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args(argv)
    try:
        actual = deterministic_summary(_load(args.result))
        expected = _load(args.baseline)
    except (KeyError, OSError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    if actual != expected:
        print("FAIL: controlled benchmark differs from the reviewed baseline")
        return 1
    print(f"PASS: controlled benchmark baseline={args.baseline.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
