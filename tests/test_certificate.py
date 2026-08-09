import json
from pathlib import Path

from reprocheck.audit import run_audit
from reprocheck.certificate import digest_payload, verify_certificate_file


def _base_payload(artifacts: object) -> dict:
    return {
        "schema_version": "1.2",
        "tool_version": "0.3.0",
        "created_at": "2026-08-09T00:00:00+00:00",
        "status": "passed",
        "artifacts": artifacts,
        "claims": [],
        "observed_metrics": {},
        "metric_evidence": {},
        "leakage": None,
        "notebook": None,
        "findings": [],
        "parameters": {},
        "certificate_sha256": "",
    }


def _write_sealed(path: Path, payload: dict) -> None:
    payload["certificate_sha256"] = ""
    payload["certificate_sha256"] = digest_payload(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_certificate_detects_payload_and_artifact_tampering(tmp_path: Path):
    source = tmp_path / "report.md"
    source.write_text("Accuracy: 100%", encoding="utf-8")
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"accuracy": 1}', encoding="utf-8")
    report = run_audit(report_path=source, metrics_path=metrics)
    certificate = tmp_path / "certificate.json"
    certificate.write_text(json.dumps(report.to_dict()), encoding="utf-8")
    assert verify_certificate_file(certificate, tmp_path) == []

    payload = json.loads(certificate.read_text(encoding="utf-8"))
    payload["status"] = "needs_review"
    certificate.write_text(json.dumps(payload), encoding="utf-8")
    assert "certificate checksum does not match its payload" in verify_certificate_file(certificate)

    certificate.write_text(json.dumps(report.to_dict()), encoding="utf-8")
    source.write_text("Accuracy: 0%", encoding="utf-8")
    errors = verify_certificate_file(certificate, tmp_path)
    assert "artifact checksum or size mismatch: report.md" in errors


def test_certificate_rejects_path_traversal_and_malformed_json(tmp_path: Path):
    certificate = tmp_path / "certificate.json"
    certificate.write_text("not-json", encoding="utf-8")
    assert verify_certificate_file(certificate)[0].startswith("certificate cannot be read")

    payload = _base_payload(
        [
            {
                "role": "report",
                "filename": "../outside.txt",
                "sha256": "0" * 64,
                "size_bytes": 1,
            }
        ]
    )
    payload["certificate_sha256"] = digest_payload(payload)
    certificate.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_certificate_file(certificate, tmp_path)
    assert "artifact filename is unsafe: '../outside.txt'" in errors


def test_certificate_rejects_malformed_descriptors(tmp_path: Path):
    certificate = tmp_path / "certificate.json"
    artifact = {
        "role": "report",
        "filename": "report.md",
        "sha256": "0" * 64,
        "size_bytes": 1,
    }
    cases = [
        ({"artifacts": "bad"}, "artifacts must be an array"),
        ({"artifacts": ["bad"]}, "descriptor 0 must be an object"),
        (
            {"artifacts": [{**artifact, "role": "../report"}]},
            "artifact role is unsafe",
        ),
        (
            {"artifacts": [artifact, artifact]},
            "duplicate artifact descriptor",
        ),
        (
            {"artifacts": [{**artifact, "sha256": "bad"}]},
            "artifact checksum is malformed",
        ),
        (
            {"artifacts": [{**artifact, "size_bytes": -1}]},
            "artifact size is malformed",
        ),
        ({"artifacts": [artifact]}, "artifact is missing"),
    ]
    for partial, expected in cases:
        payload = _base_payload(partial["artifacts"])
        _write_sealed(certificate, payload)
        assert any(expected in error for error in verify_certificate_file(certificate, tmp_path))


def test_certificate_supports_role_subdirectories_and_rejects_non_object(tmp_path: Path):
    certificate = tmp_path / "certificate.json"
    role_dir = tmp_path / "model"
    role_dir.mkdir()
    model = role_dir / "weights.bin"
    model.write_bytes(b"weights")
    import hashlib

    payload = _base_payload(
        [
            {
                "role": "model",
                "filename": "weights.bin",
                "sha256": hashlib.sha256(b"weights").hexdigest(),
                "size_bytes": 7,
            }
        ]
    )
    _write_sealed(certificate, payload)
    assert verify_certificate_file(certificate, tmp_path) == []

    certificate.write_text("[]", encoding="utf-8")
    assert verify_certificate_file(certificate) == ["certificate payload must be a JSON object"]


def test_certificate_rejects_self_consistent_schema_violation(tmp_path: Path):
    certificate = tmp_path / "certificate.json"
    artifact = {
        "role": "report",
        "filename": "report.md",
        "sha256": "0" * 64,
        "size_bytes": 0,
    }
    payload = _base_payload([artifact])
    del payload["status"]
    _write_sealed(certificate, payload)
    errors = verify_certificate_file(certificate)
    assert any(
        "schema violation" in error and "'status' is a required property" in error
        for error in errors
    )
