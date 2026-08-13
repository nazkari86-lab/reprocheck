from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = json.loads((ROOT / "results.lock.json").read_text(encoding="utf-8"))
    for name, expected in lock["results"].items():
        assert sha256(ROOT / name) == expected, name
    zero = json.loads((ROOT / "results/zero-shot-0.23.0.json").read_text(encoding="utf-8"))
    development = json.loads(
        (ROOT / "results/development-current.json").read_text(encoding="utf-8")
    )
    assert zero["phase"] == "zero-shot-frozen-0.23.0"
    assert zero["runtime_evaluator_version"] == "0.23.0"
    assert (zero["visible_cases"], zero["eligible_cases"]) == (7, 16)
    assert (zero["visible_claims"], zero["selected_claims"]) == (9, 24)
    assert development["phase"] == "development-post-v8-inspection-0.24.0"
    assert development["runtime_evaluator_version"] == "0.24.0"
    assert (development["visible_cases"], development["eligible_cases"]) == (16, 16)
    assert (development["visible_claims"], development["selected_claims"]) == (24, 24)
    print("PASS: v8 frozen zero-shot 7/16, 9/24; post-inspection 16/16, 24/24")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
