from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from reprocheck.claims import extract_claims
from reprocheck.version import __version__


def run(cases_path: Path, output: Path | None = None) -> dict[str, Any]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = []
    for spec in payload["cases"]:
        actual = [(claim.metric, claim.value) for claim in extract_claims(spec["text"])]
        expected = [(metric, float(value)) for metric, value in spec["expected"]]
        passed = _rounded_counter(actual) == _rounded_counter(expected)
        cases.append(
            {
                "id": spec["id"],
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "out_of_scope_reason": spec.get("out_of_scope_reason"),
            }
        )
    in_scope = [case for case in cases if case["out_of_scope_reason"] is None]
    result = {
        "schema": "reprocheck.representation-result.v1",
        "tool_version": __version__,
        "cases": cases,
        "summary": {
            "total_cases": len(cases),
            "in_scope_cases": len(in_scope),
            "in_scope_exact_case_accuracy": sum(case["passed"] for case in in_scope)
            / len(in_scope),
            "all_declared_expectations_accuracy": sum(case["passed"] for case in cases)
            / len(cases),
        },
        "scientific_boundary": payload["inference_boundary"],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def _rounded_counter(values: list[tuple[str, float]]) -> Counter[tuple[str, float]]:
    return Counter((metric, round(value, 12)) for metric, value in values)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("benchmarks/representation_robustness/cases-v1.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/representation-robustness.json")
    )
    args = parser.parse_args()
    benchmark = run(args.cases, args.output)
    print(json.dumps(benchmark["summary"], sort_keys=True))
