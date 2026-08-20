from __future__ import annotations

import hashlib
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest


APP_PATH = Path("benchmarks/evidence_trial_v19/adjudication_app.py")


def _module():
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_adjudication", APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dump(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _packet() -> dict:
    return {
        "schema_version": "reprocheck.evidence-trial-review-packet.v1",
        "blind": True,
        "claims": [
            {
                "claim_id": "claim-001",
                "repository": "owner/repo",
                "url": "https://github.com/owner/repo/blob/" + "a" * 40 + "/RESULTS.md",
                "claim_text": "Accuracy: 90%",
            },
            {
                "claim_id": "claim-002",
                "repository": "other/repo",
                "url": "https://github.com/other/repo/blob/" + "b" * 40 + "/RESULTS.md",
                "claim_text": "F1: 0.8",
            },
        ],
    }


def _review(packet_sha256: str, reviewer_id: str, statuses: tuple[str, str]) -> dict:
    return {
        "schema_version": "reprocheck.evidence-trial-review.v1",
        "reviewer_id": reviewer_id,
        "independent": True,
        "packet_sha256": packet_sha256,
        "reviews": [
            {
                "claim_id": f"claim-00{index}",
                "status": status,
                "rationale": f"Independent rationale {index}",
                "evidence_refs": [f"source:{index}"],
            }
            for index, status in enumerate(statuses, start=1)
        ],
    }


def _disagreement_fixture(module, tmp_path: Path) -> dict:
    packet_path = _dump(tmp_path / "packet.json", _packet())
    digest = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    first = _dump(
        tmp_path / "first.json", _review(digest, "reviewer-a", ("supported", "supported"))
    )
    second = _dump(
        tmp_path / "second.json",
        _review(digest, "reviewer-b", ("contradicted", "supported")),
    )
    return module.build_disagreement_packet(packet_path, [first, second])


def test_disagreement_packet_contains_only_disagreements_and_blinded_context(tmp_path: Path):
    module = _module()
    packet = _disagreement_fixture(module, tmp_path)
    assert packet["disagreement_count"] == 1
    assert packet["claim_count"] == 2
    assert packet["disagreements"][0]["claim"]["claim_id"] == "claim-001"
    assert packet["blind_to_evaluator_outputs"] is True
    assert "reviewer_id" not in json.dumps(packet)


def test_disagreement_packet_rejects_wrong_packet_and_same_reviewer(tmp_path: Path):
    module = _module()
    packet_path = _dump(tmp_path / "packet.json", _packet())
    digest = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    first = _dump(tmp_path / "first.json", _review(digest, "same", ("supported", "supported")))
    second_payload = _review(digest, "same", ("contradicted", "supported"))
    second = _dump(tmp_path / "second.json", second_payload)
    with pytest.raises(ValueError, match="distinct"):
        module.build_disagreement_packet(packet_path, [first, second])
    second_payload["reviewer_id"] = "other"
    second_payload["packet_sha256"] = "0" * 64
    _dump(second, second_payload)
    with pytest.raises(ValueError, match="different blinded"):
        module.build_disagreement_packet(packet_path, [first, second])


def test_disagreement_packet_rejects_private_fields_and_unsafe_links(tmp_path: Path):
    module = _module()
    payload = _packet()
    payload["claims"][0]["gold_status"] = "supported"
    packet_path = _dump(tmp_path / "packet.json", payload)
    digest = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    first = _dump(tmp_path / "first.json", _review(digest, "a", ("supported", "supported")))
    second = _dump(tmp_path / "second.json", _review(digest, "b", ("contradicted", "supported")))
    with pytest.raises(ValueError, match="leaks private"):
        module.build_disagreement_packet(packet_path, [first, second])
    payload = _packet()
    payload["claims"][0]["url"] = "javascript:alert(1)"
    packet_path = _dump(packet_path, payload)
    digest = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    _dump(first, _review(digest, "a", ("supported", "supported")))
    _dump(second, _review(digest, "b", ("contradicted", "supported")))
    with pytest.raises(ValueError, match="must use HTTPS"):
        module.build_disagreement_packet(packet_path, [first, second])


def test_adjudication_validation_and_attestation(tmp_path: Path):
    module = _module()
    packet = _disagreement_fixture(module, tmp_path)
    adjudication = {
        "adjudications": [
            {
                "claim_id": "claim-001",
                "status": "contradicted",
                "rationale": "Raw evidence conflicts with the report.",
                "evidence_refs": ["metrics.json:accuracy"],
            }
        ]
    }
    assert module.validate_adjudication(packet, adjudication, "adjudicator-a", True) == []
    attestation = module.build_attestation(packet, adjudication, "adjudicator-a")
    assert attestation["resolved_disagreement_count"] == 1
    assert attestation["evaluator_outputs_seen"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["adjudications"].clear(), "resolve all"),
        (
            lambda payload: payload["adjudications"][0].update(claim_id="claim-002"),
            "non-disagreement",
        ),
        (lambda payload: payload["adjudications"][0].update(status="maybe"), "invalid status"),
        (lambda payload: payload["adjudications"][0].update(rationale=""), "rationale"),
        (lambda payload: payload["adjudications"][0].update(evidence_refs=[]), "evidence_refs"),
    ],
)
def test_adjudication_rejects_incomplete_or_invalid_resolution(
    tmp_path: Path, mutation, message: str
):
    module = _module()
    packet = _disagreement_fixture(module, tmp_path)
    payload = {
        "adjudications": [
            {
                "claim_id": "claim-001",
                "status": "supported",
                "rationale": "Resolved from source evidence.",
                "evidence_refs": ["source:1"],
            }
        ]
    }
    mutation(payload)
    assert any(
        message in error
        for error in module.validate_adjudication(packet, payload, "adjudicator-a", True)
    )


def test_adjudication_http_app_finalizes_complete_resolution(tmp_path: Path):
    module = _module()
    packet = _disagreement_fixture(module, tmp_path)
    server = module.AdjudicationServer(("127.0.0.1", 0), module.Handler)
    server.packet = packet
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    resolution = {
        "adjudications": [
            {
                "claim_id": "claim-001",
                "status": "not_verifiable",
                "rationale": "The available source cannot decide the claim.",
                "evidence_refs": ["source:claim-001"],
            }
        ]
    }
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            assert b"Resolve reviewer disagreements" in response.read()
            assert response.headers["Content-Security-Policy"]
        with urllib.request.urlopen(base + "/app.js", timeout=5) as response:
            assert r"split(/\r?\n/)" in response.read().decode()
        body = json.dumps(
            {
                "adjudicator_id": "adjudicator-a",
                "independent": True,
                "adjudication": resolution,
            }
        ).encode()
        request = urllib.request.Request(
            base + "/api/finalize",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        assert result["attestation"]["resolved_disagreement_count"] == 1
        bad = urllib.request.Request(
            base + "/api/finalize",
            data=json.dumps(
                {"adjudicator_id": "", "independent": False, "adjudication": resolution}
            ).encode(),
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
