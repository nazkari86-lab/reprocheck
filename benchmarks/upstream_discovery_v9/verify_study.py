from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = json.loads((ROOT / "study.lock.json").read_text(encoding="utf-8"))
    for name, expected in lock["sha256"].items():
        assert sha256(ROOT / name) == expected, name
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    assert labels["parser_output_used"] is cases["parser_output_used"] is False
    assert labels["sample_size"] == len(labels["labels"]) == 3
    assert labels["eligible_cases"] == len(cases["cases"]) == 0
    assert len({label["repository"].split("/", 1)[0] for label in labels["labels"]}) == 3
    print("PASS: v9 lock valid; 3 new owners, 0 eligible cases, no visibility estimate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
