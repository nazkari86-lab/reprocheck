from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result = ROOT / "results" / "zero-shot-0.19.0.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["phase"] == "zero-shot-0.19.0"
    assert payload["runtime_evaluator_version"] == "0.19.0"
    assert payload["evaluator_commit"] == "7e5a6c087fc6f5e5df14ccde1c8436049c39c5b7"
    lock = {
        "schema_version": "reprocheck.upstream-discovery-result-lock.v1",
        "zero_shot_result": {
            "path": "results/zero-shot-0.19.0.json",
            "sha256": digest(result),
        },
        "frozen_evaluator_wheel": {
            "path": "evaluator/reprocheck-0.19.0-py3-none-any.whl",
            "sha256": digest(ROOT / "evaluator" / "reprocheck-0.19.0-py3-none-any.whl"),
        },
    }
    (ROOT / "results.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("PASS: froze zero-shot 0.19.0 result and evaluator wheel digests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
