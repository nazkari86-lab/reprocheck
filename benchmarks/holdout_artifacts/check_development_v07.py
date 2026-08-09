from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
FILES = {
    "wheel": ROOT / "evaluator" / "reprocheck-0.7.0-py3-none-any.whl",
    "manifest": ROOT / "evaluator" / "manifest-v0.7.json",
    "runner": ROOT / "run_development_v07.py",
    "annotations": ROOT / "posthoc_annotations-v0.7.json",
    "result": ROOT / "results" / "development-v0.7.json",
    "primary_result": ROOT / "results" / "zero-shot-v0.6.json",
}
EXPECTED_SHA256 = {
    "wheel": "8c182c3e2cdd41d47e296653950429d1d12cfc0837b63db565f19f2eb65a09ee",
    "manifest": "a2af45f30a964c1fc65e234bcf123524ac4a06ac394ec45ca04e1614658c529a",
    "runner": "78e172dc12a42e0dbc28890d2ba69de0161c4690d613beb84f51d002421a74b9",
    "annotations": "81b6519c34d6b34b73328e780566bc663c15ca7c100536c807648c2063faf306",
    "result": "a3bb4b0a86fe14e396615b798ededb3e6cd9c97c2c17556557606722ec595e65",
    "primary_result": "f87ac0c5c10f00c289bd4046ea0f67d07f26d4a5aba3dab74fa8f54fe935d83f",
}
SCHEMA = PROJECT / "src" / "reprocheck" / "schemas" / "holdout-development-v1.schema.json"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> None:
    for name, path in FILES.items():
        if _sha256(path) != EXPECTED_SHA256[name]:
            raise ValueError(f"frozen v0.7 development file changed: {name}")
    manifest = _load(FILES["manifest"])
    if manifest["zero_shot"] is not False:
        raise ValueError("v0.7 evaluator must remain marked as non-zero-shot")
    if manifest["sha256"] != EXPECTED_SHA256["wheel"]:
        raise ValueError("v0.7 evaluator manifest wheel binding mismatch")
    if manifest["runner"]["sha256"] != EXPECTED_SHA256["runner"]:
        raise ValueError("v0.7 evaluator manifest runner binding mismatch")
    if manifest["development_result"]["sha256"] != EXPECTED_SHA256["result"]:
        raise ValueError("v0.7 evaluator manifest result binding mismatch")

    result = _load(FILES["result"])
    schema = _load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    if result["corpus"]["posthoc_annotations_sha256"] != EXPECTED_SHA256["annotations"]:
        raise ValueError("development result annotation binding mismatch")
    if result["corpus"]["primary_v0.6_result_sha256"] != EXPECTED_SHA256["primary_result"]:
        raise ValueError("development result does not preserve the v0.6 primary reference")
    if sum(case["tp"] for case in result["cases"]) != 313:
        raise ValueError("development case totals differ from the summary")


def main() -> int:
    try:
        check()
    except (KeyError, OSError, json.JSONDecodeError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print("PASS: frozen post-holdout v0.7 development result tp=313 fp=0 fn=0 zero_shot=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
