from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

from reprocheck.claims import extract_claims
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_name(case_id: str, path: str, phase: str) -> str:
    suffix = Path(path).suffix or ".txt"
    return f"{case_id}--{path.replace('/', '__')}.{phase}{suffix}"


def matching_claim_count(text: str, snippet: str, metric: str, value: float) -> int:
    return sum(
        snippet in claim.raw_text and claim.metric == metric and abs(claim.value - value) < 1e-12
        for claim in extract_claims(text)
    )


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return [center - margin, center + margin]


def evaluate(output: Path, phase: str) -> dict[str, Any]:
    cases_manifest = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    eligible_labels = [label for label in labels["labels"] if label["eligible"]]
    assert labels["sample_size"] == sample["sample_size"] == len(labels["labels"])
    assert {label["case_id"] for label in eligible_labels} == {
        case["id"] for case in cases_manifest["cases"]
    }
    case_results = []
    for case in cases_manifest["cases"]:
        claim_results = []
        integrity = True
        texts: dict[tuple[str, str], str] = {}
        for path in case["files"]:
            for source_phase in ("before", "after"):
                filename = source_name(case["id"], path, source_phase)
                source = ROOT / "sources" / filename
                integrity = integrity and sha256(source) == lock["files"][filename]["sha256"]
                texts[(path, source_phase)] = source.read_text(encoding="utf-8")
        for claim in case["claims"]:
            before_text = texts[(claim["file"], "before")]
            after_text = texts[(claim["file"], "after")]
            before_matches = matching_claim_count(
                before_text, claim["before_snippet"], claim["metric"], float(claim["before_value"])
            )
            after_matches = matching_claim_count(
                after_text, claim["after_snippet"], claim["metric"], float(claim["after_value"])
            )
            before_source_count = before_text.count(claim["before_snippet"])
            after_source_count = after_text.count(claim["after_snippet"])
            passed = (
                before_source_count == after_source_count == 1
                and before_matches == after_matches == 1
            )
            claim_results.append(
                {
                    "file": claim["file"],
                    "metric": claim["metric"],
                    "before_value": claim["before_value"],
                    "after_value": claim["after_value"],
                    "before_source_count": before_source_count,
                    "after_source_count": after_source_count,
                    "before_parser_matches": before_matches,
                    "after_parser_matches": after_matches,
                    "passed": passed,
                }
            )
        case_results.append(
            {
                "id": case["id"],
                "repository": case["repository"],
                "pull_request": case["pull_request"],
                "source_integrity": integrity,
                "selected_claims": len(claim_results),
                "visible_claims": sum(result["passed"] for result in claim_results),
                "passed": integrity and all(result["passed"] for result in claim_results),
                "claims": claim_results,
            }
        )
    eligible_cases = len(case_results)
    visible_cases = sum(case["passed"] for case in case_results)
    selected_claims = sum(case["selected_claims"] for case in case_results)
    visible_claims = sum(case["visible_claims"] for case in case_results)
    result: dict[str, Any] = {
        "schema_version": "reprocheck.upstream-discovery-result.v2",
        "phase": phase,
        "runtime_evaluator_version": __version__,
        "evaluator_commit": cases_manifest["evaluator_commit"],
        "protocol_sha256": sha256(ROOT / "protocol.md"),
        "sample_sha256": sha256(ROOT / "sample.json"),
        "labels_sha256": sha256(ROOT / "labels.json"),
        "cases_sha256": sha256(ROOT / "cases.json"),
        "sources_lock_sha256": sha256(ROOT / "sources.lock.json"),
        "sampled_pull_requests": sample["sample_size"],
        "eligible_cases": eligible_cases,
        "eligible_yield": eligible_cases / sample["sample_size"],
        "eligible_yield_wilson_95": wilson(eligible_cases, sample["sample_size"]),
        "visible_cases": visible_cases,
        "case_visibility": visible_cases / eligible_cases if eligible_cases else 0.0,
        "case_visibility_wilson_95": wilson(visible_cases, eligible_cases),
        "selected_claims": selected_claims,
        "visible_claims": visible_claims,
        "claim_visibility": visible_claims / selected_claims if selected_claims else 0.0,
        "claim_visibility_wilson_95": wilson(visible_claims, selected_claims),
        "source_integrity": all(case["source_integrity"] for case in case_results),
        "breadth": {
            "repositories": 2,
            "independent_repository_owners": 2,
            "source_formats": ["json", "markdown_table"],
            "metric_families": ["information_retrieval_rank_metrics", "swe_bench_verified"],
        },
        "independently_frozen_raw_evidence_cases": 0,
        "raw_evidence_agreement_rate": None,
        "cases": case_results,
        "scientific_boundary": (
            "The deterministic sample estimates visibility only within five frozen, "
            "query-conditioned GitHub frames; it is not a population estimate. The two "
            "eligible cases are independent by owner but too few for a precise case-level rate."
        ),
    }
    if phase.startswith("development"):
        result["evaluation_role"] = "post_inspection_development"
        result["implementation_binding"] = "source tree committed with this result"
        development_lock = ROOT / "development.lock.json"
        if development_lock.exists():
            implementation_commit = json.loads(development_lock.read_text(encoding="utf-8"))[
                "implementation_commit"
            ]
        else:
            implementation_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        result["development_implementation_commit"] = implementation_commit
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", required=True)
    args = parser.parse_args()
    result = evaluate(args.output, args.phase)
    if not result["source_integrity"]:
        print("FAIL: source integrity mismatch")
        return 1
    print(
        f"PASS: phase={result['phase']} evaluator={result['runtime_evaluator_version']} "
        f"sample={result['sampled_pull_requests']} eligible={result['eligible_cases']} "
        f"cases={result['visible_cases']}/{result['eligible_cases']} "
        f"claims={result['visible_claims']}/{result['selected_claims']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
