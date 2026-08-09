from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from reprocheck.leakage import text_similarity
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
METHODS = ("token_jaccard", "hybrid_lexical_v1", "ordered_tokens_v1")


def run_benchmark(cases_path: Path) -> dict[str, Any]:
    source = cases_path.read_bytes()
    payload = json.loads(source)
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "reprocheck.near-duplicate-cases.v1"
    ):
        raise ValueError("unsupported near-duplicate case schema")
    threshold = payload.get("threshold")
    cases = payload.get("cases")
    if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        raise ValueError("benchmark threshold must be between 0 and 1")
    if not isinstance(cases, list) or not cases:
        raise ValueError("near-duplicate benchmark must contain cases")

    seen_ids: set[str] = set()
    normalized_cases: list[dict[str, str]] = []
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("near-duplicate benchmark case must be an object")
        required = ("id", "label", "transformation", "left", "right")
        if any(not isinstance(item.get(field), str) or not item[field] for field in required):
            raise ValueError("near-duplicate benchmark case has a missing field")
        if item["id"] in seen_ids:
            raise ValueError(f"duplicate near-duplicate benchmark id: {item['id']}")
        if item["label"] not in {"near", "unrelated"}:
            raise ValueError(f"invalid near-duplicate label: {item['label']}")
        seen_ids.add(item["id"])
        normalized_cases.append({field: item[field] for field in required})

    method_results = {
        method: _evaluate(normalized_cases, float(threshold), method) for method in METHODS
    }
    return {
        "schema": "reprocheck.near-duplicate-benchmark.v1",
        "tool_version": __version__,
        "dataset": {
            "filename": cases_path.name,
            "sha256": hashlib.sha256(source).hexdigest(),
            "cases": len(normalized_cases),
            "near_cases": sum(case["label"] == "near" for case in normalized_cases),
            "unrelated_cases": sum(case["label"] == "unrelated" for case in normalized_cases),
            "scope": payload.get("scope"),
        },
        "threshold": float(threshold),
        "methods": method_results,
    }


def _evaluate(cases: list[dict[str, str]], threshold: float, method: str) -> dict[str, Any]:
    predictions = []
    for case in cases:
        score = text_similarity(case["left"], case["right"], method)
        predictions.append(
            {
                "id": case["id"],
                "expected": case["label"],
                "predicted": "near" if score >= threshold else "unrelated",
                "similarity": round(score, 6),
            }
        )
    tp = sum(item["expected"] == item["predicted"] == "near" for item in predictions)
    tn = sum(item["expected"] == item["predicted"] == "unrelated" for item in predictions)
    fp = sum(
        item["expected"] == "unrelated" and item["predicted"] == "near" for item in predictions
    )
    fn = sum(
        item["expected"] == "near" and item["predicted"] == "unrelated" for item in predictions
    )
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "predictions": predictions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "cases-v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    hybrid = result["methods"]["hybrid_lexical_v1"]
    legacy = result["methods"]["token_jaccard"]
    ordered = result["methods"]["ordered_tokens_v1"]
    print(
        f"hybrid_precision={hybrid['precision']:.1%} hybrid_recall={hybrid['recall']:.1%} "
        f"ordered_precision={ordered['precision']:.1%} ordered_recall={ordered['recall']:.1%} "
        f"legacy_precision={legacy['precision']:.1%} legacy_recall={legacy['recall']:.1%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
