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
    if __version__ != "0.26.0":
        raise SystemExit(f"wrong evaluator version: {__version__}")
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
                "complete": tp == case_gold,
            }
        )
    false_positive = total_predicted - true_positive
    false_negative = total_gold - true_positive
    complete = sum(case["complete"] for case in cases)
    recall = true_positive / total_gold
    precision = true_positive / total_predicted if total_predicted else 0.0
    recall_ci = wilson(true_positive, total_gold)
    precision_ci = wilson(true_positive, total_predicted)
    document_visibility = complete / len(cases)
    success = (
        len(cases) >= 20
        and recall >= 0.85
        and recall_ci[0] >= 0.70
        and precision >= 0.95
        and precision_ci[0] >= 0.90
        and document_visibility >= 0.75
    )
    result = {
        "schema_version": "reprocheck.cross-project-zero-shot-result.v12",
        "phase": "zero-shot-frozen-0.26.0",
        "evaluator_commit": "0b52adad8061d77e355a200dee88b7522252f292",
        "runtime_evaluator_version": __version__,
        "eligible_documents": len(cases),
        "complete_documents": complete,
        "complete_document_visibility": document_visibility,
        "gold_claims": total_gold,
        "predicted_claims": total_predicted,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "claim_recall": recall,
        "claim_recall_wilson_95": recall_ci,
        "block_precision": precision,
        "block_precision_wilson_95": precision_ci,
        "source_integrity": True,
        "success": success,
        "cases": cases,
    }
    output = ROOT / "results" / "zero-shot-0.26.0.json"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        raise FileExistsError("v12 zero-shot result already exists")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(
        f"v12 zero-shot: documents={complete}/{len(cases)} "
        f"recall={true_positive}/{total_gold} precision={true_positive}/{total_predicted} "
        f"success={success}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
