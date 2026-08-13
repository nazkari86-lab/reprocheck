from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def verify() -> dict[str, object]:
    registration = json.loads((ROOT / "registration.json").read_text(encoding="utf-8"))
    protocol_sha256 = hashlib.sha256((ROOT / "protocol.md").read_bytes()).hexdigest()

    assert registration["status"] == "registered_unretrieved"
    assert registration["evaluator_commit"] == "2618cad2c54c1610947f4f64e4b7ba8c5302fa28"
    assert registration["evaluator_version"] == "0.18.0"
    assert registration["protocol_sha256"] == protocol_sha256
    assert registration["retrieval_started"] is False
    assert registration["labels_seen"] is False
    return {
        "status": registration["status"],
        "protocol_sha256": protocol_sha256,
        "evaluator_commit": registration["evaluator_commit"],
    }


def main() -> int:
    result = verify()
    print(
        f"PASS: prospective registration status={result['status']} "
        f"evaluator={result['evaluator_commit']} protocol={result['protocol_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
