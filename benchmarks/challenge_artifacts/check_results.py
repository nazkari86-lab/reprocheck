from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from reprocheck.claims import extract_table_claims


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SCHEMAS = PROJECT / "src" / "reprocheck" / "schemas"
ALIASES = {"map50_95": "ap", "map50": "ap50", "map75": "ap75"}
ORIGINAL_RESULT_SHA256 = "5d704dc366d3febd9703179fad4cfd6053c69f11b4a680b0f2d96b52880275fc"
FROZEN_WHEEL_SHA256 = "bcfaba70ef9bac2d463ce90f965189dba47a45d27c2772530ca23c29521fe8a0"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate(result_name: str, schema_name: str) -> dict[str, Any]:
    result = _load(ROOT / "results" / result_name)
    schema = _load(SCHEMAS / schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    evaluator = result["evaluator"]
    wheel = ROOT / "evaluator" / evaluator["filename"]
    if _sha256(wheel) != evaluator["sha256"]:
        raise ValueError(f"evaluator checksum mismatch: {wheel.name}")
    if evaluator["installed_archive_hash"] != f"sha256={evaluator['sha256']}":
        raise ValueError(f"installed archive provenance mismatch: {result_name}")
    return result


def _verify_evaluator_manifest(manifest_name: str) -> dict[str, Any]:
    manifest = _load(ROOT / "evaluator" / manifest_name)
    wheel = ROOT / "evaluator" / manifest["filename"]
    if _sha256(wheel) != manifest["sha256"]:
        raise ValueError(f"frozen evaluator manifest mismatch: {manifest_name}")
    result_entry = manifest.get("challenge_result")
    if result_entry is not None:
        result_path = ROOT / "results" / result_entry["filename"]
        if _sha256(result_path) != result_entry["sha256"]:
            raise ValueError(f"challenge result manifest mismatch: {manifest_name}")
    return manifest


def _current_parser_counts() -> tuple[Counter[str], list[tuple[str, str, float]]]:
    annotations = _load(ROOT / "annotations.json")
    declared = {
        claim["metric"]
        for artifact in annotations["artifacts"]
        for claim in artifact["expected_claims"]
    }
    totals: Counter[str] = Counter()
    extras: list[tuple[str, str, float]] = []
    for artifact in annotations["artifacts"]:
        path = ROOT / "sources" / artifact["local_path"]
        if _sha256(path) != artifact["source_sha256"]:
            raise ValueError(f"source checksum mismatch: {artifact['local_path']}")
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
                extras.append((artifact["local_path"], metric, value))
            else:
                totals["tp"] += 1
                remaining.pop(match)
        totals["fp"] += len(actual) - (len(expected) - len(remaining))
        totals["fn"] += len(remaining)
    return totals, sorted(extras)


def main() -> int:
    original_path = ROOT / "results" / "zero-shot-v0.5.json"
    if _sha256(original_path) != ORIGINAL_RESULT_SHA256:
        raise ValueError("original zero-shot result changed")
    original = _validate("zero-shot-v0.5.json", "challenge-study-v1.schema.json")
    replay = _validate("frozen-replay-v0.5.json", "challenge-study-v2.schema.json")
    development = _validate("development-v0.6.json", "challenge-study-v2.schema.json")
    frozen_manifest = _verify_evaluator_manifest("manifest.json")
    development_manifest = _verify_evaluator_manifest("manifest-v0.6.json")

    if original["summary"] != replay["summary"]:
        raise ValueError("scoped frozen replay differs from the original zero-shot summary")
    if replay["evaluator"]["sha256"] != FROZEN_WHEEL_SHA256:
        raise ValueError("frozen v0.5 evaluator changed")
    if frozen_manifest["sha256"] != replay["evaluator"]["sha256"]:
        raise ValueError("v0.5 evaluator result and manifest disagree")
    expected_development = {"tp": 1006, "fp": 2, "fn": 0}
    if {key: development["summary"][key] for key in expected_development} != expected_development:
        raise ValueError("v0.6 development result differs from the reviewed baseline")
    if development["phase"] != "development_after_challenge_inspection":
        raise ValueError("v0.6 result has an invalid scientific phase label")
    if development_manifest["sha256"] != development["evaluator"]["sha256"]:
        raise ValueError("v0.6 evaluator result and manifest disagree")

    current_counts, current_extras = _current_parser_counts()
    if current_counts != expected_development:
        raise ValueError(f"current parser differs from v0.6 baseline: {dict(current_counts)}")
    review = _load(ROOT / "posthoc_label_review.json")
    reviewed_extras = sorted(
        (case["local_path"], case["metric"], float(case["value"])) for case in review["cases"]
    )
    if current_extras != reviewed_extras:
        raise ValueError("post-hoc label review does not explain all strict false positives")

    print(
        "PASS: challenge results and current parser "
        f"zero_shot={original['summary']['tp']}/1006 "
        f"v0.6={development['summary']['tp']}/1006 "
        f"strict_fp={development['summary']['fp']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
