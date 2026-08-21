import json
from pathlib import Path

import pytest

from reprocheck.ml_registration import register_ml_protocol, verify_ml_registration


def test_registration_hash_binds_every_protocol_artifact(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.json"
    evaluator = tmp_path / "evaluate.py"
    protocol.write_text("{}\n", encoding="utf-8")
    evaluator.write_text("print('frozen')\n", encoding="utf-8")
    registration = tmp_path / "registration.json"

    payload = register_ml_protocol(tmp_path, [protocol, evaluator], registration)
    assert payload["status"] == "registered_not_executed"
    assert verify_ml_registration(tmp_path, registration) == []

    evaluator.write_text("print('changed')\n", encoding="utf-8")
    assert verify_ml_registration(tmp_path, registration) == [
        "registered artifact changed: evaluate.py"
    ]


def test_registration_rejects_missing_duplicate_outside_and_overwrite(tmp_path: Path) -> None:
    artifact = tmp_path / "protocol.json"
    artifact.write_text("{}", encoding="utf-8")
    output = tmp_path / "registration.json"
    with pytest.raises(ValueError, match="non-empty"):
        register_ml_protocol(tmp_path, [], output)
    with pytest.raises(ValueError, match="unique"):
        register_ml_protocol(tmp_path, [artifact, artifact], output)
    with pytest.raises(ValueError, match="below"):
        register_ml_protocol(tmp_path, [tmp_path.parent / "missing"], output)
    register_ml_protocol(tmp_path, [artifact], output)
    with pytest.raises(ValueError, match="already exists"):
        register_ml_protocol(tmp_path, [artifact], output)


def test_registration_verifier_reports_every_integrity_state(tmp_path: Path) -> None:
    missing = verify_ml_registration(tmp_path, tmp_path / "missing.json")
    assert missing and "cannot load" in missing[0]
    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    assert verify_ml_registration(tmp_path, array) == ["ML registration must be a JSON object"]

    artifact = tmp_path / "protocol.json"
    artifact.write_text("{}", encoding="utf-8")
    registration = tmp_path / "registration.json"
    payload = register_ml_protocol(tmp_path, [artifact], registration)
    payload.update(
        schema_version="bad",
        status="executed",
        test_labels_opened=True,
        prospective_sources_acquired=True,
        registration_sha256="0" * 64,
        artifacts="bad",
    )
    registration.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_ml_registration(tmp_path, registration)
    assert len(errors) == 6
    assert "artifacts must be an array" in errors[-1]


def test_registration_verifier_rejects_malformed_missing_and_unsafe_artifacts(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "protocol.json"
    artifact.write_text("{}", encoding="utf-8")
    registration = tmp_path / "registration.json"
    payload = register_ml_protocol(tmp_path, [artifact], registration)
    payload["artifacts"] = ["bad", {"path": "missing", "size_bytes": 0, "sha256": "0" * 64}]
    payload["registration_sha256"] = "bad"
    registration.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_ml_registration(tmp_path, registration)
    assert "ML registration artifact descriptor is malformed" in errors
    assert any("missing or unsafe" in error for error in errors)
