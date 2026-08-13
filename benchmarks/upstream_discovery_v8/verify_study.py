from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = json.loads((ROOT / "study.lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "labels-and-sources-frozen-before-evaluation"
    for name, expected in lock["sha256"].items():
        assert sha256(ROOT / name) == expected, name
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    assert labels["parser_output_used"] is False
    assert cases["parser_output_used"] is False
    assert labels["sample_size"] == len(labels["labels"]) == 994
    assert labels["eligible_cases"] == len(cases["cases"]) == 16
    assert len({case["repository"].split("/", 1)[0] for case in cases["cases"]}) == 16
    print("PASS: v8 pre-evaluation lock valid; 994 labels, 16 independent eligible owners")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
