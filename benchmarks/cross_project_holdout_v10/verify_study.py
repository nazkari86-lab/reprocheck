from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = json.loads((ROOT / "study.lock.json").read_text())
    for relative, expected in lock["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise SystemExit(f"study hash mismatch: {relative}")
    for source in lock["sources"]:
        if digest(ROOT / source["file"]) != source["sha256"]:
            raise SystemExit(f"source hash mismatch: {source['file']}")
    print(f"v10 study verified: {len(lock['sources'])} sources, {lock['selected_claims']} claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
