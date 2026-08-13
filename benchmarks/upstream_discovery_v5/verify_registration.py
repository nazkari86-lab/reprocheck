from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict[str, Any]:
    registration = json.loads((ROOT / "registration.json").read_text(encoding="utf-8"))
    assert registration["status"] == "registered_unretrieved"
    assert registration["retrieval_started"] is False
    assert registration["candidates_seen"] is False
    assert registration["labels_seen"] is False
    assert not (ROOT / "raw").exists()
    assert not (ROOT / "frames.json").exists()
    assert not (ROOT / "sample.json").exists()
    assert sha256(ROOT / "protocol.md") == registration["protocol_sha256"]
    assert sha256(ROOT / "retrieve.py") == registration["retrieval_script_sha256"]
    assert sha256(ROOT / registration["evaluator_wheel"]) == registration["evaluator_wheel_sha256"]
    for relative, expected in registration["prior_exposure_inputs"].items():
        assert sha256(ROOT / relative) == expected
    return {
        "status": registration["status"],
        "evaluator_commit": registration["evaluator_commit"],
        "wheel_sha256": registration["evaluator_wheel_sha256"],
        "protocol_sha256": registration["protocol_sha256"],
        "query_frames": registration["query_frames"],
        "maximum_sample_size": registration["maximum_sample_size"],
        "exclusion_inputs": len(registration["prior_exposure_inputs"]),
    }


def main() -> int:
    result = verify()
    print(
        "PASS: v5 registration "
        f"status={result['status']} evaluator={result['evaluator_commit']} "
        f"wheel={result['wheel_sha256']} frames={result['query_frames']} "
        f"max-sample={result['maximum_sample_size']} "
        f"exclusion-inputs={result['exclusion_inputs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
