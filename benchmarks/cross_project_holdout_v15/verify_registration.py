from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    registration = json.loads((ROOT / "registration.json").read_text())
    for relative, expected in registration["sha256"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"registration hash mismatch: {relative}")
    print("v15 registration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
