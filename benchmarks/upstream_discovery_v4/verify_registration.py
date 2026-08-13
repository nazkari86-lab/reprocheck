from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED_COMMIT = "4b1ffdf633723c2672449aa15198d259f80b7568"
EXPECTED_WHEEL_SHA256 = "f73561ca61a1bb04211ef4a4d73c7250c0e969c35105077d219be54a61f810fd"
EXPECTED_QUERIES = [
    '"correct benchmark results" in:title,body is:merged',
    '"corrected benchmark results" in:title,body is:merged',
    '"fix incorrect benchmark" in:title,body is:merged',
    '"incorrect benchmark result" in:title,body is:merged',
    '"wrong benchmark result" in:title,body is:merged',
    '"fix evaluation results" in:title,body is:merged',
    '"correct evaluation results" in:title,body is:merged',
    '"incorrect evaluation results" in:title,body is:merged',
    '"wrong score" benchmark in:title,body is:merged',
    '"correct score" benchmark in:title,body is:merged',
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict[str, object]:
    registration = json.loads((ROOT / "registration.json").read_text(encoding="utf-8"))
    assert registration["status"] == "registered_unretrieved"
    assert registration["evaluator_commit"] == EXPECTED_COMMIT
    assert registration["evaluator_version"] == "0.20.0"
    assert registration["protocol_sha256"] == _sha256(ROOT / "protocol.md")

    wheel = ROOT / registration["evaluator_wheel"]
    assert registration["evaluator_wheel_sha256"] == EXPECTED_WHEEL_SHA256
    assert _sha256(wheel) == EXPECTED_WHEEL_SHA256

    for relative_path, expected_sha256 in registration["prior_exposure_inputs"].items():
        assert _sha256(ROOT / relative_path) == expected_sha256

    source = (ROOT / "retrieve.py").read_text(encoding="utf-8")
    for query in EXPECTED_QUERIES:
        assert repr(query) in source
    assert 'SEED = "reprocheck-upstream-v4"' in source
    assert "selected = candidates[:25]" in source

    assert registration["retrieval_started"] is False
    assert registration["candidates_seen"] is False
    assert registration["labels_seen"] is False
    return {
        "status": registration["status"],
        "protocol_sha256": registration["protocol_sha256"],
        "evaluator_commit": registration["evaluator_commit"],
        "wheel_sha256": EXPECTED_WHEEL_SHA256,
        "exclusion_inputs": len(registration["prior_exposure_inputs"]),
        "queries": len(EXPECTED_QUERIES),
        "maximum_sample": len(EXPECTED_QUERIES) * 25,
    }


def main() -> int:
    result = verify()
    print(
        f"PASS: v4 registration status={result['status']} "
        f"evaluator={result['evaluator_commit']} wheel={result['wheel_sha256']} "
        f"queries={result['queries']} max-sample={result['maximum_sample']} "
        f"exclusion-inputs={result['exclusion_inputs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
