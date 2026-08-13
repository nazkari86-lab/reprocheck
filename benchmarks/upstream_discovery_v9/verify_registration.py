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
    assert registration["extractor_commit"] == "2eff4e8"
    assert registration["extractor_version"] == "0.24.0"
    assert not any((ROOT / name).exists() for name in ("raw", "frames.json", "sample.json"))
    for relative, expected in registration["sha256"].items():
        assert sha256(ROOT / relative) == expected, relative
    print("PASS: v9 registered before retrieval; extractor=2eff4e8; max-sample=1000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
