from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from reprocheck.claims import extract_claims


ROOT = Path(__file__).parents[1] / "benchmarks" / "cross_project_holdout_v12"


def normalized_key(line: int, metric: str, value: float) -> tuple[int, str, float]:
    return (line, metric, round(float(value), 12))


def test_v12_frozen_zero_shot_result_remains_immutable():
    result = ROOT / "results" / "zero-shot-0.26.0.json"
    assert hashlib.sha256(result.read_bytes()).hexdigest() == (
        "1a8938f686caea152bc0d5bb8025886fa5633abc272f8c56560c4c8e2a1d5ad5"
    )


def test_post_inspection_parser_exactly_matches_v12_selected_blocks():
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))["labels"]
    samples = {
        item["sample_rank"]: item
        for item in json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))["samples"]
    }
    eligible = gold_total = predicted_total = 0
    mismatches: list[tuple[int, list[tuple[int, str, float]], list[tuple[int, str, float]]]] = []
    for case in labels:
        if case["eligible"] is not True:
            continue
        eligible += 1
        start, end = case["block_lines"]
        gold = Counter(
            normalized_key(claim["line"], claim["metric"], claim["value"])
            for claim in case["claims"]
        )
        source = ROOT / samples[case["rank"]]["source_file"]
        predicted = Counter(
            normalized_key(claim.line, claim.metric, claim.value)
            for claim in extract_claims(source.read_text(encoding="utf-8"))
            if start <= claim.line <= end
        )
        gold_total += sum(gold.values())
        predicted_total += sum(predicted.values())
        if gold != predicted:
            mismatches.append(
                (
                    case["rank"],
                    list((gold - predicted).elements()),
                    list((predicted - gold).elements()),
                )
            )
    assert (eligible, gold_total, predicted_total) == (20, 190, 190)
    assert mismatches == []
