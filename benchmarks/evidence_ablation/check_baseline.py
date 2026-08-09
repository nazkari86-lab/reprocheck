from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def deterministic_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": result["schema_version"],
        "tool_version": result["tool_version"],
        "design": result["design"],
        "case_counts": result["case_counts"],
        "systems": result["systems"],
        "pairwise_mcnemar": result["pairwise_mcnemar"],
        "case_matrix": [
            {
                "id": case["id"],
                "family": case["family"],
                "defect_present": case["defect_present"],
                "detected": {
                    system: details["detected"] for system, details in case["systems"].items()
                },
            }
            for case in result["cases"]
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check the evidence-layer ablation baseline")
    parser.add_argument(
        "--result", type=Path, default=ROOT.parent.parent / "outputs/evidence-ablation.json"
    )
    parser.add_argument("--baseline", type=Path, default=ROOT / "baseline-v1.json")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        actual = deterministic_summary(_load(args.result))
    except (KeyError, OSError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    serialized = json.dumps(actual, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        args.baseline.write_text(serialized, encoding="utf-8")
        print(f"wrote baseline={args.baseline.resolve()}")
        return 0
    try:
        expected = _load(args.baseline)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    if actual != expected:
        print("FAIL: evidence-layer ablation differs from the reviewed baseline")
        return 1
    print(f"PASS: evidence-layer ablation baseline={args.baseline.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
