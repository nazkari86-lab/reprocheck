from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from reprocheck.leakage import find_text_matches, text_similarity
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
THRESHOLD = 0.8


def _corpus(train_size: int, test_size: int, *, common_token: bool) -> tuple[list[str], list[str]]:
    prefix = "shared " if common_token else ""
    train = [f"{prefix}topic{i % 97} sample{i} measurement{i * 17 + 3}" for i in range(train_size)]
    test = []
    for index in range(test_size):
        if index % 2 == 0:
            test.append(train[(index * 37) % train_size])
        else:
            test.append(f"{prefix}novel{index} independent{index} unseen{index * 19 + 5}")
    return train, test


def _exhaustive_matches(train: list[str], test: list[str]) -> list[tuple[int, int, float]]:
    matches = []
    for test_index, test_text in enumerate(test):
        scores = [
            text_similarity(test_text, train_text, "ordered_tokens_v1") for train_text in train
        ]
        best = max(range(len(scores)), key=lambda index: (scores[index], -index))
        if scores[best] >= THRESHOLD:
            matches.append((test_index, best, scores[best]))
    return matches


def _run_case(name: str, train_size: int, test_size: int, common_token: bool) -> dict[str, Any]:
    train, test = _corpus(train_size, test_size, common_token=common_token)
    search = find_text_matches(
        train,
        test,
        threshold=THRESHOLD,
        method="ordered_tokens_v1",
    )
    exhaustive = search.exhaustive_pairs
    return {
        "name": name,
        "train_rows": train_size,
        "test_rows": test_size,
        "expected_matches": (test_size + 1) // 2,
        "observed_matches": len(search.matches),
        "exhaustive_pairs": exhaustive,
        "candidate_pairs": search.candidate_pairs,
        "scored_pairs": search.scored_pairs,
        "candidate_reduction": 1 - search.candidate_pairs / exhaustive,
        "expensive_score_reduction": 1 - search.scored_pairs / exhaustive,
        "common_token": common_token,
    }


def run_benchmark() -> dict[str, Any]:
    verification_train, verification_test = _corpus(300, 100, common_token=True)
    indexed = find_text_matches(
        verification_train,
        verification_test,
        threshold=THRESHOLD,
        method="ordered_tokens_v1",
    )
    indexed_tuples = [
        (match.test_index, match.train_index, match.similarity) for match in indexed.matches
    ]
    exhaustive_tuples = _exhaustive_matches(verification_train, verification_test)
    if indexed_tuples != exhaustive_tuples:
        raise AssertionError("indexed ordered-token search differs from exhaustive search")
    cases = [
        _run_case("sparse_vocabulary", 10_000, 1_000, False),
        _run_case("shared_common_token", 2_000, 200, True),
    ]
    if any(case["observed_matches"] != case["expected_matches"] for case in cases):
        raise AssertionError("scalability corpus lost a known matching pair")
    return {
        "schema": "reprocheck.text-index-scalability.v1",
        "tool_version": __version__,
        "method": "ordered_tokens_v1",
        "threshold": THRESHOLD,
        "correctness": {
            "indexed_equals_exhaustive": True,
            "verified_pairs": len(verification_train) * len(verification_test),
        },
        "cases": cases,
        "limitations": [
            "Pair-count reduction is deterministic; wall-clock speed is environment-dependent.",
            "The generated corpora test index mechanics, not natural-language accuracy.",
            "A ubiquitous token can eliminate candidate-set reduction, although the multiset bound still avoids expensive sequence scoring.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for case in result["cases"]:
        print(
            f"{case['name']}: exhaustive={case['exhaustive_pairs']} "
            f"candidates={case['candidate_pairs']} scored={case['scored_pairs']} "
            f"score_reduction={case['expensive_score_reduction']:.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
