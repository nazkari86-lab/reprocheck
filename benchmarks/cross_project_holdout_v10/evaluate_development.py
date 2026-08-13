from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from reprocheck.claims import extract_claims
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [center - margin, center + margin]


def main() -> int:
    labels = json.loads((ROOT / "labels.json").read_text())
    sample = json.loads((ROOT / "sample.json").read_text())
    lock = json.loads((ROOT / "study.lock.json").read_text())
    for source in lock["sources"]:
        if digest(ROOT / source["file"]) != source["sha256"]:
            raise SystemExit(f"source hash mismatch: {source['file']}")
    by_rank = {item["sample_rank"]: item for item in sample["samples"]}
    cases: list[dict[str, Any]] = []
    for label in labels["labels"]:
        if label["eligible"] is not True:
            continue
        item = by_rank[label["rank"]]
        extracted = extract_claims((ROOT / item["source_file"]).read_text())
        claim_results = []
        for expected in label["claims"]:
            visible = any(
                claim.line == expected["line"]
                and claim.metric == expected["metric"]
                and abs(claim.value - float(expected["value"])) < 1e-9
                for claim in extracted
            )
            claim_results.append({
                "line": expected["line"],
                "metric": expected["metric"],
                "value": expected["value"],
                "visible": visible,
            })
        cases.append({
            "rank": label["rank"],
            "repository": label["repository"],
            "selected_claims": len(claim_results),
            "visible_claims": sum(item["visible"] for item in claim_results),
            "passed": all(item["visible"] for item in claim_results),
            "claims": claim_results,
        })
    visible_documents = sum(case["passed"] for case in cases)
    selected_claims = sum(case["selected_claims"] for case in cases)
    visible_claims = sum(case["visible_claims"] for case in cases)
    result = {
        "schema_version": "reprocheck.cross-project-development-result.v10",
        "phase": "post-inspection-development-current",
        "runtime_evaluator_version": __version__,
        "eligible_documents": len(cases),
        "visible_documents": visible_documents,
        "document_visibility": visible_documents / len(cases),
        "document_visibility_wilson_95": wilson(visible_documents, len(cases)),
        "selected_claims": selected_claims,
        "visible_claims": visible_claims,
        "claim_visibility": visible_claims / selected_claims,
        "claim_visibility_wilson_95": wilson(visible_claims, selected_claims),
        "source_integrity": True,
        "cases": cases,
        "scientific_boundary": (
            "This score was produced after inspecting v10 failures. It measures development "
            "coverage only and must not be reported as zero-shot or external validation."
        ),
    }
    output = ROOT / "results" / "development-current.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(
        f"v10 development: documents={visible_documents}/{len(cases)} "
        f"claims={visible_claims}/{selected_claims}"
    )
    return 0 if visible_documents == len(cases) and visible_claims == selected_claims else 1


if __name__ == "__main__":
    raise SystemExit(main())
