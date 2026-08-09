from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=ROOT / "baseline-v1.json")
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    comparable = {
        **result,
        "methods": {
            method: {key: value for key, value in values.items() if key != "predictions"}
            for method, values in result["methods"].items()
        },
    }
    if comparable != baseline:
        raise SystemExit("FAIL: near-duplicate benchmark differs from frozen baseline")
    print(f"PASS: near-duplicate benchmark baseline={args.baseline.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
