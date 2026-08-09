from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
WHEEL = ROOT.parent / "holdout_artifacts" / "evaluator" / "reprocheck-0.7.0-py3-none-any.whl"
SCHEMA = PROJECT / "src" / "reprocheck" / "schemas" / "cross-domain-holdout-study-v1.schema.json"
FILES = {
    "preregistration.json": "ce3938ea9019b2555564b68e0100f11fbcc1ed83048ec506270c94aaf6317cbf",
    "source_manifest.json": "906a865805d535adc65068e32f9c008727835436e98da9b2c7ee82c9ce2ac3da",
    "build_annotations.py": "8bcc7d5fed3653b593423358215cbf3fc0112a34ba9074d361d4fcbf3561d8f4",
    "annotations.json": "8d9b583536a768f2fb6c69b5a5b5e170ec580e4716ff987eb69e61b4e1407109",
    "annotation.lock.json": "81fbb64974a757f56a70230a7c93abccdc326a3f8572970b1d02c2a9de94fc6e",
    "run_zero_shot.py": "bbcc19e39f9308cca694f3ba3d79e36c611261d7fb2f6d8fbed880e0aaa25e04",
    "evaluation.lock.json": "94c9ea7f95bb55fe5a1a787b6fda405442e387c26d10fd27b7d72b47c056fb93",
    "results/zero-shot-v0.7.json": "74c7547eee265a19c8ee2d0269f384583dddb96228d4c53eef5022e1654a1b57",
    "posthoc_review.json": "7b6e9a9d9718621bd65a053a7e7c3b3d720b5d186e4be596a4db9afc1e5aee34",
}
WHEEL_SHA256 = "8c182c3e2cdd41d47e296653950429d1d12cfc0837b63db565f19f2eb65a09ee"
EXPECTED_FAILURES = {
    "paddleclas/docs/en/models/RedNet_en.md": (0, 0, 10),
    "paddleclas/docs/en/models/TNT_en.md": (0, 0, 2),
    "timm/README.md": (6, 0, 24),
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> None:
    for relative_path, expected in FILES.items():
        if _sha256(ROOT / relative_path) != expected:
            raise ValueError(f"locked cross-domain file changed: {relative_path}")
    if _sha256(WHEEL) != WHEEL_SHA256:
        raise ValueError("frozen v0.7 evaluator changed")
    result = _load(ROOT / "results" / "zero-shot-v0.7.json")
    schema = _load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    corpus = result["corpus"]
    for key, filename in (
        ("preregistration_sha256", "preregistration.json"),
        ("source_manifest_sha256", "source_manifest.json"),
        ("annotations_sha256", "annotations.json"),
        ("annotation_lock_sha256", "annotation.lock.json"),
    ):
        if corpus[key] != FILES[filename]:
            raise ValueError(f"result binding mismatch: {key}")
    summary = result["summary"]
    for key in ("tp", "fp", "fn"):
        if sum(case[key] for case in result["cases"]) != summary[key]:
            raise ValueError(f"case {key} values do not sum to primary summary")
    failures = {
        case["local_path"]: (case["tp"], case["fp"], case["fn"])
        for case in result["cases"]
        if not case["exact"]
    }
    if failures != EXPECTED_FAILURES:
        raise ValueError("primary failure set changed")
    review = _load(ROOT / "posthoc_review.json")
    if (
        review["primary_result_modified"] is not False
        or review["annotation_errors_identified"] != 0
    ):
        raise ValueError("post-hoc review violates the primary evidence boundary")
    if sum(group["false_negatives"] for group in review["error_groups"]) != summary["fn"]:
        raise ValueError("post-hoc review does not explain every false negative")


def main() -> int:
    try:
        check()
    except (KeyError, OSError, json.JSONDecodeError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print(
        "PASS: immutable cross-domain v0.7 zero-shot tp=259 fp=0 fn=36 precision=100% recall=87.80%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
