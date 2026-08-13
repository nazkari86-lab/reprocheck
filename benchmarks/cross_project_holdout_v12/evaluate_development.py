from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from reprocheck.claims import extract_claims
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
Key = tuple[int, str, float]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [center - margin, center + margin]


def normalized_key(line: int, metric: str, value: float) -> Key:
    return (line, metric, round(float(value), 12))


def main() -> int:
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "study.lock.json").read_text(encoding="utf-8"))
    for relative, expected in lock["immutable_files"].items():
        if digest(ROOT / relative) != expected:
            raise SystemExit(f"study hash mismatch: {relative}")
    by_rank = {item["sample_rank"]: item for item in sample["samples"]}
    cases: list[dict[str, Any]] = []
    total_gold = total_predicted = true_positive = 0
    for label in labels["labels"]:
        if label["eligible"] is not True:
            continue
        item = by_rank[label["rank"]]
        extracted = extract_claims((ROOT / item["source_file"]).read_text(encoding="utf-8"))
        start, end = label["block_lines"]
        gold = Counter(
            normalized_key(claim["line"], claim["metric"], claim["value"])
            for claim in label["claims"]
        )
        predicted = Counter(
            normalized_key(claim.line, claim.metric, claim.value)
            for claim in extracted
            if start <= claim.line <= end
        )
        matched = gold & predicted
        tp = sum(matched.values())
        case_gold = sum(gold.values())
        case_predicted = sum(predicted.values())
        total_gold += case_gold
        total_predicted += case_predicted
        true_positive += tp
        cases.append(
            {
                "rank": label["rank"],
                "repository": label["repository"],
                "block_lines": label["block_lines"],
                "gold_claims": case_gold,
                "predicted_claims": case_predicted,
                "true_positive": tp,
                "false_positive": case_predicted - tp,
                "false_negative": case_gold - tp,
                "exact": gold == predicted,
            }
        )
    false_positive = total_predicted - true_positive
    false_negative = total_gold - true_positive
    exact = sum(case["exact"] for case in cases)
    recall = true_positive / total_gold
    precision = true_positive / total_predicted if total_predicted else 0.0
    result = {
        "schema_version": "reprocheck.cross-project-development-result.v12",
        "phase": "post-inspection-development-current",
        "runtime_evaluator_version": __version__,
        "eligible_documents": len(cases),
        "exact_documents": exact,
        "exact_document_rate": exact / len(cases),
        "gold_claims": total_gold,
        "predicted_claims": total_predicted,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "claim_recall": recall,
        "claim_recall_wilson_95": wilson(true_positive, total_gold),
        "block_precision": precision,
        "block_precision_wilson_95": wilson(true_positive, total_predicted),
        "source_integrity": True,
        "cases": cases,
        "scientific_boundary": (
            "This score was produced after inspecting v12 failures. It measures development "
            "coverage only and must not be reported as zero-shot or external validation."
        ),
    }
    output = ROOT / "results" / "development-current.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"v12 development: documents={exact}/{len(cases)} "
        f"recall={true_positive}/{total_gold} precision={true_positive}/{total_predicted}"
    )
    return 0 if exact == len(cases) and false_positive == 0 and false_negative == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
