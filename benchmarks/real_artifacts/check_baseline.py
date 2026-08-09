from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
DEFAULT_RESULT = ROOT.parents[1] / "outputs" / "real-study.json"
DEFAULT_BASELINE = ROOT / "baseline-v6.json"


def deterministic_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "reprocheck.real-artifact-baseline.v6",
        "tool_version": __version__,
        "study_schema_version": result["schema_version"],
        "corpus": result["corpus"],
        "reprocheck": result["reprocheck"],
        "naive_inline_baseline": result["naive_inline_baseline"],
        "format_aware_baseline": result["format_aware_baseline"],
        "paired_claim_recall_delta": result["paired_claim_recall_delta"],
        "paired_claim_recall_delta_vs_format_aware": result[
            "paired_claim_recall_delta_vs_format_aware"
        ],
        "mutation_detection": result["mutation_detection"],
        "by_repository": result["by_repository"],
        "excluded_as_environment_dependent": ["latency_ms"],
        "excluded_as_verbose": ["cases"],
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check the deterministic real-study baseline")
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace the baseline after an intentional, reviewed behavior change",
    )
    args = parser.parse_args(argv)
    summary = deterministic_summary(_load(args.result))
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        args.baseline.write_text(serialized, encoding="utf-8")
        print(f"wrote baseline={args.baseline.resolve()}")
        return 0
    expected = _load(args.baseline)
    if summary != expected:
        print("FAIL: real-artifact study differs from the reviewed baseline")
        return 1
    print(f"PASS: deterministic real-artifact baseline={args.baseline.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
