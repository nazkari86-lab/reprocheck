from pathlib import Path

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
