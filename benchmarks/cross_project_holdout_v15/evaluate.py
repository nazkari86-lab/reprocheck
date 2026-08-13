from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13.evaluate import normalized_key, wilson
from reprocheck.claims import extract_claims
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if __version__ != "0.28.0":
        raise SystemExit(f"wrong evaluator version: {__version__}")
    labels = json.loads((ROOT / "labels.json").read_text())
    sample = json.loads((ROOT / "sample.json").read_text())
    lock = json.loads((ROOT / "study.lock.json").read_text())
    ontology = set(json.loads((ROOT / "supported-ontology.json").read_text())["canonical_metrics"])
    for relative, expected in lock["immutable_files"].items():
        if digest(ROOT / relative) != expected:
            raise SystemExit(f"study hash mismatch: {relative}")
    by_rank = {item["sample_rank"]: item for item in sample["samples"]}
    cases = []
    total_gold = total_predicted = true_positive = 0
    for label in labels["labels"]:
        if not label["eligible"]:
            continue
        item = by_rank[label["rank"]]
        start, end = label["block_lines"]
        gold = Counter(normalized_key(c["line"], c["metric"], c["value"]) for c in label["claims"])
        predicted = Counter(
            normalized_key(c.line, c.metric, c.value)
            for c in extract_claims((ROOT / item["source_file"]).read_text())
            if start <= c.line <= end and c.metric in ontology
        )
        matched = gold & predicted
        tp, ng, np = sum(matched.values()), sum(gold.values()), sum(predicted.values())
        total_gold += ng
        total_predicted += np
        true_positive += tp
        cases.append(
            {
                "rank": label["rank"],
                "repository": label["repository"],
                "block_lines": label["block_lines"],
                "gold_claims": ng,
                "predicted_claims": np,
                "true_positive": tp,
                "false_positive": np - tp,
                "false_negative": ng - tp,
                "exact": gold == predicted,
            }
        )
    exact = sum(case["exact"] for case in cases)
    recall = true_positive / total_gold if total_gold else 0.0
    precision = true_positive / total_predicted if total_predicted else 0.0
    recall_ci, precision_ci = (
        wilson(true_positive, total_gold),
        wilson(true_positive, total_predicted),
    )
    exact_rate = exact / len(cases) if cases else 0.0
    success = (
        len(cases) >= 20
        and recall >= 0.85
        and recall_ci[0] >= 0.70
        and precision >= 0.95
        and precision_ci[0] >= 0.90
        and exact_rate >= 0.75
    )
    result = {
        "schema_version": "reprocheck.cross-project-zero-shot-result.v15",
        "phase": "zero-shot-v15-frozen-0.28.0",
        "evaluator_commit": "76614583ae8676ba6ed309b43ca8865e707d8c4e",
        "runtime_evaluator_version": __version__,
        "eligible_documents": len(cases),
        "exact_documents": exact,
        "exact_document_rate": exact_rate,
        "gold_claims": total_gold,
        "predicted_claims": total_predicted,
        "true_positive": true_positive,
        "false_positive": total_predicted - true_positive,
        "false_negative": total_gold - true_positive,
        "claim_recall": recall,
        "claim_recall_wilson_95": recall_ci,
        "block_precision": precision,
        "block_precision_wilson_95": precision_ci,
        "source_integrity": True,
        "success": success,
        "cases": cases,
    }
    output = ROOT / "results" / "zero-shot-0.28.0.json"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        raise FileExistsError("v15 zero-shot result already exists")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        f"v15 zero-shot: exact={exact}/{len(cases)} recall={true_positive}/{total_gold} precision={true_positive}/{total_predicted} success={success}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
