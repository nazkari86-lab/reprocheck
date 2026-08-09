from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
RESULT = ROOT / "results" / "zero-shot-v0.6.json"
SCHEMA = PROJECT / "src" / "reprocheck" / "schemas" / "holdout-study-v1.schema.json"
WHEEL = (
    PROJECT
    / "benchmarks"
    / "challenge_artifacts"
    / "evaluator"
    / "reprocheck-0.6.0-py3-none-any.whl"
)
LOCKED_SHA256 = {
    "preregistration.json": "478cf7370e097be4c95577710513154514917f1190cee1d7cfb033043648f67a",
    "source_manifest.json": "dcf58f8015401ce9d66bd3cc988a0c1e949df1df6e3b751eace9214755448ada",
    "annotations.json": "be84838acfb26ccb62558d6fa1a4470320b2c0aac5c469e159d3390eaaa95828",
    "annotation.lock.json": "a1ea814e23a8765b9787d5a5a3b8f2d56e2de24e98d3cfc018531782508eae05",
    "run_zero_shot.py": "d7b4320d2e47f23e79a38f5ceaebef417ae44d360559475e7bf0ede642981fee",
    "results/zero-shot-v0.6.json": "f87ac0c5c10f00c289bd4046ea0f67d07f26d4a5aba3dab74fa8f54fe935d83f",
    "posthoc_review.json": "b60069e3662e711405365d588251dcbad5a7bef8a431504b735cd7a9863cec6d",
}
EVALUATOR_SHA256 = "c9cbc753f0027d2815dcc9105603580495c2ee9797364c84e6d3f3f38b84e1f6"
EXPECTED_SUMMARY = {"tp": 297, "fp": 67, "fn": 16}
EXPECTED_FAILURES = {
    "ultralytics/docs/en/models/yolo-world.md": {"tp": 8, "fp": 16, "fn": 16},
    "ultralytics/docs/en/models/yolov7.md": {"tp": 44, "fp": 51, "fn": 0},
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> None:
    for relative_path, expected_hash in LOCKED_SHA256.items():
        path = ROOT / relative_path
        if _sha256(path) != expected_hash:
            raise ValueError(f"locked holdout file changed: {relative_path}")
    if _sha256(WHEEL) != EVALUATOR_SHA256:
        raise ValueError("frozen v0.6 evaluator wheel changed")

    result = _load(RESULT)
    schema = _load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)

    evaluator = result["evaluator"]
    if evaluator["sha256"] != EVALUATOR_SHA256:
        raise ValueError("result does not identify the frozen evaluator")
    if evaluator["installed_archive_hash"] != f"sha256={EVALUATOR_SHA256}":
        raise ValueError("installed evaluator provenance is invalid")
    corpus = result["corpus"]
    for result_key, filename in (
        ("preregistration_sha256", "preregistration.json"),
        ("source_manifest_sha256", "source_manifest.json"),
        ("annotations_sha256", "annotations.json"),
        ("annotation_lock_sha256", "annotation.lock.json"),
    ):
        if corpus[result_key] != LOCKED_SHA256[filename]:
            raise ValueError(f"result input binding mismatch: {result_key}")

    summary = result["summary"]
    if {key: summary[key] for key in EXPECTED_SUMMARY} != EXPECTED_SUMMARY:
        raise ValueError("primary holdout summary changed")
    if sum(case["tp"] for case in result["cases"]) != summary["tp"]:
        raise ValueError("case true positives do not sum to the summary")
    if sum(case["fp"] for case in result["cases"]) != summary["fp"]:
        raise ValueError("case false positives do not sum to the summary")
    if sum(case["fn"] for case in result["cases"]) != summary["fn"]:
        raise ValueError("case false negatives do not sum to the summary")
    failures = {
        case["local_path"]: {key: case[key] for key in ("tp", "fp", "fn")}
        for case in result["cases"]
        if not case["exact"]
    }
    if failures != EXPECTED_FAILURES:
        raise ValueError("holdout failure set changed")

    review = _load(ROOT / "posthoc_review.json")
    if review["primary_result_modified"] is not False:
        raise ValueError("post-hoc review must not modify the primary result")
    if review["strict_primary_result"]["tp"] != summary["tp"]:
        raise ValueError("post-hoc review does not reference the strict primary result")
    if sum(group["strict_fp"] for group in review["error_groups"]) != summary["fp"]:
        raise ValueError("post-hoc groups do not explain all strict false positives")
    if sum(group["strict_fn"] for group in review["error_groups"]) != summary["fn"]:
        raise ValueError("post-hoc groups do not explain all strict false negatives")


def main() -> int:
    try:
        check()
    except (KeyError, OSError, json.JSONDecodeError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print("PASS: immutable preregistered holdout tp=297 fp=67 fn=16 precision=81.59% recall=94.89%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
