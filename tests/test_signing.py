import base64
import json
import os
from importlib.resources import files
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jsonschema import Draft202012Validator

from reprocheck.audit import run_audit
from reprocheck.cli import main
from reprocheck.signing import (
    generate_keypair,
    sign_certificate,
    verify_certificate_signature,
)


PASSWORD = b"correct horse battery staple"


def _certificate(root: Path) -> Path:
    report_path = root / "report.md"
    predictions_path = root / "predictions.csv"
    report_path.write_text("Accuracy: 100%", encoding="utf-8")
    predictions_path.write_text("y_true,y_pred\ncat,cat\ndog,dog\n", encoding="utf-8")
    report = run_audit(report_path=report_path, predictions_path=predictions_path)
    certificate = root / "audit.json"
    certificate.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return certificate


def test_ed25519_signature_roundtrip_and_tamper_detection(tmp_path: Path):
    import reprocheck

    assert reprocheck.generate_keypair is generate_keypair
    assert reprocheck.sign_certificate is sign_certificate
    assert reprocheck.verify_certificate_signature is verify_certificate_signature
    certificate = _certificate(tmp_path)
    private_key = tmp_path / "signing-private.pem"
    public_key = tmp_path / "signing-public.pem"
    signature = tmp_path / "audit.sig.json"
    fingerprint = generate_keypair(private_key, public_key, PASSWORD)
    assert len(fingerprint) == 64
    if os.name == "posix":
        assert private_key.stat().st_mode & 0o777 == 0o600

    payload = sign_certificate(certificate, private_key, signature, PASSWORD)
    schema = json.loads(
        files("reprocheck")
        .joinpath("schemas/certificate-signature-v1.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["public_key"]["fingerprint_sha256"] == fingerprint
    assert verify_certificate_signature(certificate, signature, public_key, tmp_path) == []

    original_certificate = certificate.read_text(encoding="utf-8")
    certificate.write_text(original_certificate + " ", encoding="utf-8")
    certificate_errors = verify_certificate_signature(certificate, signature, public_key, tmp_path)
    assert any("certificate checksum" in error for error in certificate_errors)
    assert "Ed25519 signature is invalid" in certificate_errors
    certificate.write_text(original_certificate, encoding="utf-8")

    tampered = json.loads(signature.read_text(encoding="utf-8"))
    raw_signature = bytearray(base64.b64decode(tampered["signature"]["value"]))
    raw_signature[0] ^= 1
    tampered["signature"]["value"] = base64.b64encode(raw_signature).decode("ascii")
    signature.write_text(json.dumps(tampered), encoding="utf-8")
    assert "Ed25519 signature is invalid" in verify_certificate_signature(
        certificate, signature, public_key
    )


def test_signature_rejects_wrong_key_password_permissions_and_invalid_certificate(tmp_path: Path):
    certificate = _certificate(tmp_path)
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    signature = tmp_path / "signature.json"
    generate_keypair(private_key, public_key, PASSWORD)

    with pytest.raises(ValueError, match="refusing to overwrite"):
        generate_keypair(private_key, public_key, PASSWORD)
    with pytest.raises(ValueError, match="at least 12"):
        generate_keypair(tmp_path / "short-private", tmp_path / "short-public", b"short")
    with pytest.raises(ValueError, match="cannot be loaded"):
        sign_certificate(certificate, private_key, signature, b"wrong password value")

    if os.name == "posix":
        private_key.chmod(0o644)
        with pytest.raises(ValueError, match="permissions are too open"):
            sign_certificate(certificate, private_key, signature, PASSWORD)
        private_key.chmod(0o600)

    invalid_certificate = tmp_path / "invalid.json"
    invalid_certificate.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to sign invalid certificate"):
        sign_certificate(invalid_certificate, private_key, signature, PASSWORD)

    sign_certificate(certificate, private_key, signature, PASSWORD)
    other_private = tmp_path / "other-private.pem"
    other_public = tmp_path / "other-public.pem"
    generate_keypair(other_private, other_public, PASSWORD)
    errors = verify_certificate_signature(certificate, signature, other_public)
    assert "signer public key does not match the trusted public key" in errors

    wrong_type_private = tmp_path / "rsa-private.pem"
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_type_private.write_bytes(
        rsa_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(PASSWORD),
        )
    )
    wrong_type_private.chmod(0o600)
    with pytest.raises(ValueError, match="private key is not Ed25519"):
        sign_certificate(certificate, wrong_type_private, signature, PASSWORD)

    wrong_type_public = tmp_path / "rsa-public.pem"
    wrong_type_public.write_bytes(
        rsa_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    assert any(
        "trusted public key cannot be loaded" in error
        for error in verify_certificate_signature(certificate, signature, wrong_type_public)
    )


def test_signing_cli_uses_environment_password_and_fails_closed(tmp_path: Path, monkeypatch):
    certificate = _certificate(tmp_path)
    private_key = tmp_path / "cli-private.pem"
    public_key = tmp_path / "cli-public.pem"
    signature = tmp_path / "cli-signature.json"
    monkeypatch.setenv("TEST_REPROCHECK_PASSWORD", PASSWORD.decode())
    assert (
        main(
            [
                "keygen",
                "--private-key",
                str(private_key),
                "--public-key",
                str(public_key),
                "--password-env",
                "TEST_REPROCHECK_PASSWORD",
            ]
        )
        == 0
    )
    other_private = tmp_path / "other-cli-private.pem"
    other_public = tmp_path / "other-cli-public.pem"
    generate_keypair(other_private, other_public, PASSWORD)
    assert (
        main(
            [
                "verify-signature",
                "--certificate",
                str(certificate),
                "--signature",
                str(signature),
                "--public-key",
                str(other_public),
            ]
        )
        == 1
    )
    assert (
        main(
            [
                "sign",
                "--certificate",
                str(certificate),
                "--private-key",
                str(private_key),
                "--output",
                str(signature),
                "--password-env",
                "TEST_REPROCHECK_PASSWORD",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "verify-signature",
                "--certificate",
                str(certificate),
                "--signature",
                str(signature),
                "--public-key",
                str(public_key),
                "--artifact-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    monkeypatch.delenv("TEST_REPROCHECK_PASSWORD")
    assert (
        main(
            [
                "sign",
                "--certificate",
                str(certificate),
                "--private-key",
                str(private_key),
                "--password-env",
                "TEST_REPROCHECK_PASSWORD",
            ]
        )
        == 2
    )
    assert (
        main(
            [
                "keygen",
                "--private-key",
                str(tmp_path / "missing-env-private.pem"),
                "--public-key",
                str(tmp_path / "missing-env-public.pem"),
                "--password-env",
                "TEST_REPROCHECK_PASSWORD",
            ]
        )
        == 2
    )


def test_signature_envelope_descriptor_and_fingerprint_are_verified(tmp_path: Path):
    certificate = _certificate(tmp_path)
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    signature = tmp_path / "signature.json"
    generate_keypair(private_key, public_key, PASSWORD)
    payload = sign_certificate(certificate, private_key, signature, PASSWORD)
    payload["certificate"]["filename"] = "other.json"
    payload["certificate"]["size_bytes"] += 1
    payload["certificate"]["sha256"] = "0" * 64
    payload["public_key"]["fingerprint_sha256"] = "0" * 64
    signature.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_certificate_signature(certificate, signature, public_key)
    assert "signature certificate filename does not match" in errors
    assert "signature certificate size does not match" in errors
    assert "signature certificate checksum does not match" in errors
    assert "embedded public key fingerprint does not match" in errors


@pytest.mark.parametrize("content", ["not-json", "[]", '{"schema_version":"wrong"}'])
def test_signature_envelope_rejects_malformed_input(tmp_path: Path, content: str):
    certificate = _certificate(tmp_path)
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    signature = tmp_path / "signature.json"
    generate_keypair(private_key, public_key, PASSWORD)
    signature.write_text(content, encoding="utf-8")
    assert verify_certificate_signature(certificate, signature, public_key)
