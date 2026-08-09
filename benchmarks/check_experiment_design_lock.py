from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "benchmarks/experiment-design-v1.lock.json"


def main() -> int:
    payload = json.loads(LOCK.read_text(encoding="utf-8"))
    failures = []
    for relative, expected in payload["files"].items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            failures.append(f"{relative}: expected={expected} actual={actual}")
    if failures:
        print("FAIL: experiment design lock mismatch")
        for failure in failures:
            print(failure)
        return 1
    print(f"PASS: experiment design lock files={len(payload['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
