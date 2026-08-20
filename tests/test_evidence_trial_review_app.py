from __future__ import annotations

import hashlib
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest


APP_PATH = Path("benchmarks/evidence_trial_v19/review_app.py")


def _module():
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_review", APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _packet() -> dict:
    return {
        "schema_version": "reprocheck.evidence-trial-review-packet.v1",
        "blind": True,
        "claims": [
            {
                "claim_id": "claim-001",
                "candidate_id": "candidate-001",
                "repository": "owner/repo",
                "url": "https://github.com/owner/repo/blob/" + "a" * 40 + "/RESULTS.md",
                "block": {"start": 3, "end": 3},
                "claim_text": "Accuracy: 90%",
                "declared_metric": "accuracy",
                "declared_value": 0.9,
                "stratum": "natural_unadjudicated",
                "evidence_tier": "report_only",
            },
            {
                "claim_id": "claim-002",
                "candidate_id": "candidate-002",
                "repository": "other/repo",
                "url": "https://github.com/other/repo/blob/" + "b" * 40 + "/report.md",
                "block": {"start": 8, "end": 9},
                "claim_text": "F1: 0.8",
                "declared_metric": "f1",
                "declared_value": 0.8,
                "stratum": "natural_unadjudicated",
                "evidence_tier": "supplied_metrics",
            },
        ],
    }


def _review(packet_sha256: str) -> dict:
    return {
        "schema_version": "reprocheck.evidence-trial-review.v1",
        "reviewer_id": "independent-reviewer-a",
        "independent": True,
        "packet_sha256": packet_sha256,
        "reviews": [
            {
                "claim_id": claim_id,
                "status": status,
                "rationale": "Checked the immutable source and available evidence.",
                "evidence_refs": [f"immutable:{claim_id}"],
            }
            for claim_id, status in (
                ("claim-001", "not_verifiable"),
                ("claim-002", "supported"),
            )
        ],
    }


def test_load_packet_is_blind_and_hash_bound(tmp_path: Path):
    module = _module()
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(_packet()) + "\n", encoding="utf-8")
    assert len(module.load_packet(path)["claims"]) == 2
    payload = _packet()
    payload["claims"][0]["gold_status"] = "supported"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="leaks private"):
        module.load_packet(path)
    payload = _packet()
    payload["claims"][0]["url"] = "javascript:alert(1)"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must use HTTPS"):
        module.load_packet(path)


def test_review_validation_and_attestation():
    module = _module()
    packet = _packet()
    digest = "a" * 64
    review = _review(digest)
    assert module.validate_review(packet, digest, review) == []
    attestation = module.build_attestation(digest, review, 2)
    assert attestation["reviewed_claim_count"] == 2
    assert attestation["gold_labels_seen"] is False
    assert len(attestation["review_sha256"]) == 64


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda review: review.update(reviewer_id=""), "reviewer_id"),
        (lambda review: review.update(independent=False), "independence"),
        (lambda review: review.update(packet_sha256="0" * 64), "different blinded"),
        (lambda review: review["reviews"].pop(), "every claim"),
        (lambda review: review["reviews"][0].update(status="maybe"), "invalid status"),
        (lambda review: review["reviews"][0].update(rationale=""), "rationale"),
        (lambda review: review["reviews"][0].update(evidence_refs=[]), "evidence_refs"),
        (lambda review: review["reviews"][0].update(gold_status="supported"), "unexpected"),
    ],
)
def test_review_validation_rejects_incomplete_or_leaky_rows(mutation, message: str):
    module = _module()
    digest = "a" * 64
    review = _review(digest)
    mutation(review)
    assert any(message in error for error in module.validate_review(_packet(), digest, review))


def test_review_http_app_finalizes_only_complete_response(tmp_path: Path):
    module = _module()
    packet = _packet()
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    server = module.ReviewServer(("127.0.0.1", 0), module.Handler)
    server.packet = packet
    server.packet_sha256 = digest
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            assert b"Blinded claim review" in response.read()
            assert response.headers["Content-Security-Policy"]
        with urllib.request.urlopen(base + "/app.js", timeout=5) as response:
            script = response.read().decode("utf-8")
            assert r"split(/\r?\n/)" in script
        with urllib.request.urlopen(base + "/api/packet", timeout=5) as response:
            served = json.loads(response.read())
            assert served["packet_sha256"] == digest
            assert served["packet"] == packet
        body = json.dumps({"review": _review(digest)}).encode()
        request = urllib.request.Request(
            base + "/api/finalize",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        assert result["attestation"]["reviewed_claim_count"] == 2
        incomplete = _review(digest)
        incomplete["reviews"].pop()
        bad = urllib.request.Request(
            base + "/api/finalize",
            data=json.dumps({"review": incomplete}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(bad, timeout=5)
        assert error.value.code == 422
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
