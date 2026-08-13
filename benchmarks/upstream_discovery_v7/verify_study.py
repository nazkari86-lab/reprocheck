from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    study = json.loads((ROOT / "study.lock.json").read_text(encoding="utf-8"))
    for relative, expected in study["sha256"].items():
        if relative == "evaluate.py":
            continue
        assert sha256(ROOT / relative) == expected, relative
    lock = json.loads((ROOT / "results.lock.json").read_text(encoding="utf-8"))
    frozen = ROOT / lock["result"]
    assert sha256(frozen) == lock["sha256"]
    zero = json.loads(frozen.read_text(encoding="utf-8"))
    development = json.loads(
        (ROOT / "results" / "development-current.json").read_text(encoding="utf-8")
    )
    assert (zero["visible_cases"], zero["eligible_cases"]) == (1, 4)
    assert (zero["visible_claims"], zero["selected_claims"]) == (5, 11)
    assert development["phase"] == "development-post-inspection-0.23.0"
    assert (development["visible_cases"], development["eligible_cases"]) == (3, 4)
    assert (development["visible_claims"], development["selected_claims"]) == (9, 11)
    print("PASS: v7 zero-shot 1/4, 5/11; development 3/4, 9/11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
