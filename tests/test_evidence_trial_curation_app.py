from __future__ import annotations

import hashlib
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest


ROOT = Path("benchmarks/evidence_trial_v19")


def _module():
    path = ROOT / "curation_app.py"
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_curation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(module):
    packet_path = ROOT / "curation-packet.json"
    packet = module.load_packet(packet_path)
    packet["packet_sha256"] = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    sources = module.verify_sources(packet_path, packet)
    candidate = packet["candidates"][0]
    first_line = sources[candidate["candidate_id"]].read_text(encoding="utf-8").splitlines()[0]
    enrollment = {
        "schema_version": "reprocheck.evidence-trial-enrollment.v1",
        "curator_id": "curator-fixture",
        "independent_from_evaluator": True,
        "candidate_manifest_sha256": packet["candidate_manifest"]["sha256"],
        "claims": [
            {
                "claim_id": "claim-001",
                "candidate_id": candidate["candidate_id"],
                "block": {"start": 1, "end": 1},
                "claim_text": first_line,
                "declared_metric": None,
                "declared_value": None,
                "stratum": "natural_unadjudicated",
                "evidence_tier": "report_only",
            }
        ],
    }
    return packet, sources, enrollment


def test_curation_packet_and_all_frozen_sources_verify():
    module = _module()
    packet, sources, _ = _fixture(module)
    assert packet["candidate_count"] == 60
    assert len(sources) == 60


def test_curation_packet_rejects_unsafe_source_link(tmp_path: Path):
    module = _module()
    payload = json.loads((ROOT / "curation-packet.json").read_text(encoding="utf-8"))
    payload["candidates"][0]["immutable_url"] = "javascript:alert(1)"
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe immutable URL"):
        module.load_packet(packet)


def test_enrollment_validation_and_complete_attestation():
    module = _module()
    packet, sources, enrollment = _fixture(module)
    assert module.validate_enrollment(packet, sources, enrollment) == []
    reviewed = [row["candidate_id"] for row in packet["candidates"]]
    attestation = module.build_attestation(packet, enrollment, reviewed)
    assert attestation["reviewed_candidate_count"] == 60
    assert attestation["claim_count"] == 1
    assert attestation["outcome_labels_seen"] is False
    with pytest.raises(ValueError, match="all candidate"):
        module.build_attestation(packet, enrollment, reviewed[:-1])


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda row: row.update(claim_id="bad"), "invalid claim_id"),
        (lambda row: row.update(candidate_id="candidate-999"), "unknown candidate"),
        (lambda row: row.update(block={"start": 0, "end": 1}), "invalid line range"),
        (lambda row: row.update(claim_text="changed"), "does not match"),
        (lambda row: row.update(stratum="controlled_mutation"), "natural_unadjudicated"),
        (lambda row: row.update(evidence_tier="unknown"), "invalid evidence tier"),
        (lambda row: row.update(declared_value=True), "invalid declared value"),
    ],
)
def test_enrollment_validation_rejects_tampering(mutation, message: str):
    module = _module()
    packet, sources, enrollment = _fixture(module)
    mutation(enrollment["claims"][0])
    assert any(
        message in error for error in module.validate_enrollment(packet, sources, enrollment)
    )


def test_local_http_app_serves_sources_and_validates_finalize():
    module = _module()
    packet, sources, enrollment = _fixture(module)
    server = module.CurationServer(("127.0.0.1", 0), module.Handler)
    server.packet = packet
    server.source_paths = sources
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            assert response.status == 200
            assert b"Source-only curator" in response.read()
            assert response.headers["Content-Security-Policy"]
        with urllib.request.urlopen(base + "/app.js", timeout=5) as response:
            script = response.read().decode("utf-8")
            assert r"split(/\r?\n/)" in script
            assert r"join('\n')" in script
        candidate_id = packet["candidates"][0]["candidate_id"]
        with urllib.request.urlopen(base + f"/api/source/{candidate_id}", timeout=5) as response:
            assert response.read() == sources[candidate_id].read_bytes()
        reviewed = [row["candidate_id"] for row in packet["candidates"]]
        body = json.dumps({"enrollment": enrollment, "reviewed_candidate_ids": reviewed}).encode(
            "utf-8"
        )
        request = urllib.request.Request(
            base + "/api/finalize",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        assert result["attestation"]["claim_count"] == 1
        bad = urllib.request.Request(
            base + "/api/finalize",
            data=b"{}",
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
