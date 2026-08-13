from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    registration = json.loads((ROOT / "registration.json").read_text(encoding="utf-8"))
    assert registration["status"] == "registered_unretrieved"
    assert registration["extractor_commit"] == "5fdb6a6"
    assert not (ROOT / "frames.json").exists()
    assert not (ROOT / "sample.json").exists()
    assert not (ROOT / "raw").exists()
    for relative, expected in registration["sha256"].items():
        assert sha256(ROOT / relative) == expected, relative
    print("PASS: v6 registered before retrieval; extractor=5fdb6a6; max-sample=90")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
