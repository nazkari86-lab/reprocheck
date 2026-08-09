from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from reprocheck.claims import extract_table_claims


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "benchmarks" / "challenge_artifacts"
SCHEMAS = ROOT / "src" / "reprocheck" / "schemas"
ALIASES = {"map50_95": "ap", "map50": "ap50", "map75": "ap75"}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate(result_name: str, schema_name: str) -> dict[str, Any]:
    result = _load(CHALLENGE / "results" / result_name)
    schema = _load(SCHEMAS / schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    return result


def test_frozen_zero_shot_result_and_scoped_replay_are_immutable():
    original = _validate("zero-shot-v0.5.json", "challenge-study-v1.schema.json")
    replay = _validate("frozen-replay-v0.5.json", "challenge-study-v2.schema.json")

    assert _sha256(CHALLENGE / "results" / "zero-shot-v0.5.json") == (
        "5d704dc366d3febd9703179fad4cfd6053c69f11b4a680b0f2d96b52880275fc"
    )
    assert original["summary"] == replay["summary"]
    assert original["summary"] | {"phase": replay["phase"]} == {
        "tp": 18,
        "fp": 0,
        "fn": 988,
        "precision": 1.0,
        "precision_wilson_95": [0.8241154494176252, 1.0],
        "recall": 0.017892644135188866,
        "recall_wilson_95": [0.011347385114434337, 0.028105931128429885],
        "artifact_exact_rate": 0.22807017543859648,
        "claim_artifact_exact_rate": 0.011235955056179775,
        "phase": "frozen_evaluator_replay",
    }
    assert replay["evaluator"]["sha256"] == (
        "bcfaba70ef9bac2d463ce90f965189dba47a45d27c2772530ca23c29521fe8a0"
    )


def test_development_result_is_bound_to_the_v060_wheel():
    result = _validate("development-v0.6.json", "challenge-study-v2.schema.json")
    assert result["phase"] == "development_after_challenge_inspection"
    assert result["summary"] == {
        "tp": 1006,
        "fp": 2,
        "fn": 0,
        "precision": 0.998015873015873,
        "precision_wilson_95": [0.9927944469110758, 0.9994557234713238],
        "recall": 1.0,
        "recall_wilson_95": [0.9961958390305965, 1.0],
        "artifact_exact_rate": 0.9912280701754386,
        "claim_artifact_exact_rate": 1.0,
    }
    wheel = CHALLENGE / "evaluator" / result["evaluator"]["filename"]
    assert _sha256(wheel) == result["evaluator"]["sha256"]
    assert result["evaluator"]["version"] == "0.6.0"


def test_current_table_parser_matches_frozen_labels_and_explains_extras():
    annotations = _load(CHALLENGE / "annotations.json")
    review = _load(CHALLENGE / "posthoc_label_review.json")
    declared = {
        claim["metric"]
        for artifact in annotations["artifacts"]
        for claim in artifact["expected_claims"]
    }
    totals: Counter[str] = Counter()
    unmatched_actual: list[tuple[str, str, float]] = []

    for artifact in annotations["artifacts"]:
        path = CHALLENGE / "sources" / artifact["local_path"]
        assert _sha256(path) == artifact["source_sha256"]
        expected = [
            (claim["metric"], float(claim["value"])) for claim in artifact["expected_claims"]
        ]
        actual = []
        for claim in extract_table_claims(path.read_text(encoding="utf-8")):
            metric = ALIASES.get(claim.metric, claim.metric)
            if metric in declared:
                actual.append((metric, claim.value))

        remaining = list(expected)
        for metric, value in actual:
            match = next(
                (
                    index
                    for index, (expected_metric, expected_value) in enumerate(remaining)
                    if metric == expected_metric and abs(value - expected_value) <= 1e-9
                ),
                None,
            )
            if match is None:
                unmatched_actual.append((artifact["local_path"], metric, value))
            else:
                totals["tp"] += 1
                remaining.pop(match)
        totals["fp"] += len(actual) - (len(expected) - len(remaining))
        totals["fn"] += len(remaining)

    assert totals == {"tp": 1006, "fp": 2, "fn": 0}
    expected_posthoc = sorted(
        (case["local_path"], case["metric"], float(case["value"])) for case in review["cases"]
    )
    assert sorted(unmatched_actual) == expected_posthoc
    assert review["created_after_evaluator_output_inspection"] is True
    assert review["primary_frozen_annotations_modified"] is False
