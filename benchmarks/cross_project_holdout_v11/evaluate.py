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
    if __version__ != "0.25.0":
        raise SystemExit(f"wrong evaluator version: {__version__}")
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "study.lock.json").read_text(encoding="utf-8"))
    for relative, expected in lock["immutable_files"].items():
        if digest(ROOT / relative) != expected:
            raise SystemExit(f"study hash mismatch: {relative}")
    by_rank = {item["sample_rank"]: item for item in sample["samples"]}
    cases: list[dict[str, Any]] = []
    for label in labels["labels"]:
        if label["eligible"] is not True:
            continue
        item = by_rank[label["rank"]]
        extracted = extract_claims((ROOT / item["source_file"]).read_text(encoding="utf-8"))
        claim_results = []
        for expected in label["claims"]:
            visible = any(
                claim.line == expected["line"]
                and claim.metric == expected["metric"]
                and abs(claim.value - float(expected["value"])) < 1e-9
                for claim in extracted
            )
            claim_results.append({**expected, "visible": visible})
        cases.append(
            {
                "rank": label["rank"],
                "repository": label["repository"],
                "selected_claims": len(claim_results),
                "visible_claims": sum(item["visible"] for item in claim_results),
                "passed": all(item["visible"] for item in claim_results),
                "claims": claim_results,
            }
        )
    visible_documents = sum(case["passed"] for case in cases)
    selected_claims = sum(case["selected_claims"] for case in cases)
    visible_claims = sum(case["visible_claims"] for case in cases)
    result = {
        "schema_version": "reprocheck.cross-project-zero-shot-result.v11",
        "phase": "zero-shot-frozen-0.25.0",
        "evaluator_commit": "792ad73",
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
        "success": (
            len(cases) >= 20
            and visible_claims / selected_claims >= 0.85
            and wilson(visible_claims, selected_claims)[0] >= 0.70
            and visible_documents / len(cases) >= 0.75
        ),
        "cases": cases,
    }
    output = ROOT / "results" / "zero-shot-0.25.0.json"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        raise FileExistsError("v11 zero-shot result already exists")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(
        f"v11 zero-shot: documents={visible_documents}/{len(cases)} "
        f"claims={visible_claims}/{selected_claims} success={result['success']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
