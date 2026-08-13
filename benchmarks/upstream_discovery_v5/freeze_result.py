from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result = ROOT / "results" / "zero-shot-0.21.0.json"
    lock_path = ROOT / "results.lock.json"
    if lock_path.exists():
        raise FileExistsError(lock_path)
    if not result.exists():
        raise FileNotFoundError(result)
    payload = json.loads(result.read_text(encoding="utf-8"))
    if (
        payload["phase"] != "zero-shot-frozen-0.21.0"
        or payload["runtime_evaluator_version"] != "0.21.0"
    ):
        raise ValueError("unexpected frozen result identity")
    lock = {
        "schema_version": "reprocheck.upstream-discovery-result-lock.v5",
        "result": str(result.relative_to(ROOT)),
        "sha256": sha256(result),
        "protocol_sha256": sha256(ROOT / "protocol.md"),
        "sample_sha256": sha256(ROOT / "sample.json"),
        "labels_sha256": sha256(ROOT / "labels.json"),
        "cases_sha256": sha256(ROOT / "cases.json"),
        "sources_lock_sha256": sha256(ROOT / "sources.lock.json"),
    }
    lock_path.write_text(json.dumps(lock, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: locked {lock['result']} sha256={lock['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
