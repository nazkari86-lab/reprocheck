from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from reprocheck.claims import extract_claims
from reprocheck.version import __version__

import verify_study


ROOT = Path(__file__).resolve().parent


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [center - margin, center + margin]


def matches(actual: Any, expected: dict[str, Any]) -> bool:
    return (
        actual.line == expected["line"]
        and actual.metric == expected["metric"]
        and abs(actual.value - float(expected["value"])) < 1e-9
    )


def evaluate(output: Path) -> dict[str, Any]:
    verify_study.main()
    labels = json.loads((ROOT / "labels.json").read_text())
    sample = json.loads((ROOT / "sample.json").read_text())
    by_rank = {item["sample_rank"]: item for item in sample["samples"]}
    cases = []
    for label in labels["labels"]:
        if label["eligible"] is not True:
            continue
        item = by_rank[label["rank"]]
        text = (ROOT / item["source_file"]).read_text(encoding="utf-8")
        extracted = extract_claims(text)
        claim_results = []
        for expected in label["claims"]:
            found = [claim for claim in extracted if matches(claim, expected)]
            claim_results.append({
                "metric": expected["metric"],
                "value": expected["value"],
                "line": expected["line"],
                "snippet": expected["snippet"],
                "visible": bool(found),
                "matches": len(found),
            })
        cases.append({
            "rank": label["rank"],
            "repository": label["repository"],
            "path": label["path"],
            "blob_sha": item["blob_sha"],
            "selected_claims": len(claim_results),
            "visible_claims": sum(result["visible"] for result in claim_results),
            "passed": all(result["visible"] for result in claim_results),
            "claims": claim_results,
            "extracted_claim_count": len(extracted),
        })
    visible_cases = sum(case["passed"] for case in cases)
    selected_claims = sum(case["selected_claims"] for case in cases)
    visible_claims = sum(case["visible_claims"] for case in cases)
    claim_interval = wilson(visible_claims, selected_claims)
    case_interval = wilson(visible_cases, len(cases))
    result = {
        "schema_version": "reprocheck.cross-project-result.v10",
        "phase": "preregistered-zero-shot-frozen-0.24.0",
        "runtime_evaluator_version": __version__,
        "extractor_commit": "734a3d5b4ec421bcccacede69df4f86f7c1900fe",
        "sampled_documents": sample["sample_size"],
        "reviewed_documents": sum(label["review_status"] == "reviewed" for label in labels["labels"]),
        "eligible_documents": len(cases),
        "independent_owners": len({case["repository"].split("/", 1)[0].casefold() for case in cases}),
        "visible_documents": visible_cases,
        "document_visibility": visible_cases / len(cases),
        "document_visibility_wilson_95": case_interval,
        "selected_claims": selected_claims,
        "visible_claims": visible_claims,
        "claim_visibility": visible_claims / selected_claims,
        "claim_visibility_wilson_95": claim_interval,
        "thresholds": {
            "minimum_eligible_documents": 15,
            "claim_visibility": 0.85,
            "claim_visibility_wilson_lower": 0.70,
            "document_visibility_for_9_of_10": 0.85,
        },
        "threshold_pass": {
            "minimum_eligible_documents": len(cases) >= 15,
            "claim_visibility": visible_claims / selected_claims >= 0.85,
            "claim_visibility_wilson_lower": claim_interval[0] >= 0.70,
            "document_visibility_for_9_of_10": visible_cases / len(cases) >= 0.85,
        },
        "cases": cases,
        "scientific_boundary": (
            "This is a preregistered, query-conditioned GitHub Markdown holdout with one "
            "document per previously unseen owner. It estimates visibility within the frozen "
            "search frames, not all software documentation. No v0.24.0 extractor change follows "
            "source retrieval or annotation."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(
        f"v10 zero-shot: documents={visible_cases}/{len(cases)} "
        f"claims={visible_claims}/{selected_claims} "
        f"claim_ci=[{claim_interval[0]:.4f},{claim_interval[1]:.4f}]"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
