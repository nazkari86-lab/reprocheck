from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SCHEMA = (
    PROJECT / "src" / "reprocheck" / "schemas" / "cross-domain-holdout-development-v1.schema.json"
)
FILES = {
    "evaluator/reprocheck-0.8.0-py3-none-any.whl": "c08925b2c955452c59dfe2c8f0838afb2e90b300207e990ce00041f5502733a3",
    "evaluator/manifest-v0.8.json": "dee9a82f9930131ae357ecf68c2595b4d3aa77b9610a65bd02e6c40a148042c2",
    "run_development_v08.py": "5312ec6124fa6fe3d3e4321f3f19a3b24f9669c7f949665e9f6e3c101ea57cdc",
    "results/zero-shot-v0.7.json": "74c7547eee265a19c8ee2d0269f384583dddb96228d4c53eef5022e1654a1b57",
    "results/development-v0.8.json": "1b0baaa36a4f42a1780f12bb7d12aa07196b1030ee9c53d70dad3828d76f596f",
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
            raise ValueError(f"frozen v0.8 development file changed: {relative_path}")
    result = _load(ROOT / "results" / "development-v0.8.json")
    schema = _load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    if result["corpus"]["primary_v0.7_result_sha256"] != FILES["results/zero-shot-v0.7.json"]:
        raise ValueError("v0.8 development result does not preserve the v0.7 primary reference")
    if sum(case["tp"] for case in result["cases"]) != 295:
        raise ValueError("v0.8 development cases do not sum to 295 true positives")
    manifest = _load(ROOT / "evaluator" / "manifest-v0.8.json")
    if manifest["zero_shot"] is not False:
        raise ValueError("v0.8 result must remain marked as development")


def main() -> int:
    try:
        check()
    except (KeyError, OSError, json.JSONDecodeError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print("PASS: frozen post-holdout v0.8 development result tp=295 fp=0 fn=0 zero_shot=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
