from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED_COMMIT = "7e5a6c087fc6f5e5df14ccde1c8436049c39c5b7"
EXPECTED_WHEEL_SHA256 = "fb76d6ae2d9cfe6a2400e3b5be68525d54d87041f17aa3c80ad50e4233697c8e"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict[str, object]:
    registration = json.loads((ROOT / "registration.json").read_text(encoding="utf-8"))
    assert registration["status"] == "registered_unretrieved"
    assert registration["evaluator_commit"] == EXPECTED_COMMIT
    assert registration["evaluator_version"] == "0.19.0"
    assert registration["protocol_sha256"] == _sha256(ROOT / "protocol.md")

    wheel = ROOT / registration["evaluator_wheel"]
    assert registration["evaluator_wheel_sha256"] == EXPECTED_WHEEL_SHA256
    assert _sha256(wheel) == EXPECTED_WHEEL_SHA256

    for relative_path, expected_sha256 in registration["prior_exposure_inputs"].items():
        assert _sha256(ROOT / relative_path) == expected_sha256

    assert registration["retrieval_started"] is False
    assert registration["candidates_seen"] is False
    assert registration["labels_seen"] is False
    return {
        "status": registration["status"],
        "protocol_sha256": registration["protocol_sha256"],
        "evaluator_commit": registration["evaluator_commit"],
        "wheel_sha256": EXPECTED_WHEEL_SHA256,
        "exclusion_inputs": len(registration["prior_exposure_inputs"]),
    }


def main() -> int:
    result = verify()
    print(
        f"PASS: v3 registration status={result['status']} "
        f"evaluator={result['evaluator_commit']} wheel={result['wheel_sha256']} "
        f"exclusion-inputs={result['exclusion_inputs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
