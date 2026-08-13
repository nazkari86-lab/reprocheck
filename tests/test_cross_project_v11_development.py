from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reprocheck.claims import extract_claims


ROOT = Path(__file__).parents[1] / "benchmarks" / "cross_project_holdout_v11"


def test_v11_frozen_zero_shot_result_remains_immutable():
    result = ROOT / "results" / "zero-shot-0.25.0.json"
    assert hashlib.sha256(result.read_bytes()).hexdigest() == (
        "3f6397a72d8a387a363bc8bda99991b0108a022f9910e44598d26391006fd662"
    )


def test_post_inspection_parser_covers_all_v11_selected_claims():
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))["labels"]
    samples = {
        item["sample_rank"]: item
        for item in json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))["samples"]
    }
    eligible = 0
    selected = 0
    missing: list[tuple[int, int, str, float]] = []
    for case in labels:
        if case["eligible"] is not True:
            continue
        eligible += 1
        source = ROOT / samples[case["rank"]]["source_file"]
        extracted = extract_claims(source.read_text(encoding="utf-8"))
        for expected in case["claims"]:
            selected += 1
            visible = any(
                claim.line == expected["line"]
                and claim.metric == expected["metric"]
                and abs(claim.value - float(expected["value"])) < 1e-9
                for claim in extracted
            )
            if not visible:
                missing.append(
                    (
                        case["rank"],
                        expected["line"],
                        expected["metric"],
                        float(expected["value"]),
                    )
                )
    assert (eligible, selected) == (25, 237)
    assert missing == []
