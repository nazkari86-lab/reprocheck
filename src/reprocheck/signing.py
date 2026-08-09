from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from jsonschema import Draft202012Validator, FormatChecker

from .certificate import verify_certificate_file


_DOMAIN = b"ReproCheck detached signature v1\x00"
_SIGNATURE_SCHEMA = json.loads(
    files("reprocheck")
    .joinpath("schemas/certificate-signature-v1.schema.json")
    .read_text(encoding="utf-8")
)
_SIGNATURE_VALIDATOR = Draft202012Validator(_SIGNATURE_SCHEMA, format_checker=FormatChecker())


def generate_keypair(private_path: Path, public_path: Path, password: bytes) -> str:
    _validate_password(password)
    for path in (private_path, public_path):
        if path.exists():
            raise ValueError(f"refusing to overwrite existing key: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _write_bytes_atomic(private_path, private_pem, mode=0o600)
    _write_bytes_atomic(public_path, public_pem, mode=0o644)
    return _fingerprint(_raw_public_key(public_key))


def sign_certificate(
    certificate_path: Path,
    private_key_path: Path,
    signature_path: Path,
    password: bytes,
) -> dict[str, Any]:
    _validate_password(password)
    certificate_errors = verify_certificate_file(certificate_path)
    if certificate_errors:
        raise ValueError(f"refusing to sign invalid certificate: {certificate_errors[0]}")
    _require_private_permissions(private_key_path)
    certificate = certificate_path.read_bytes()
    private_key = _load_private_key(private_key_path, password)
    public_raw = _raw_public_key(private_key.public_key())
    payload: dict[str, Any] = {
        "schema_version": "reprocheck.signature.v1",
        "algorithm": "Ed25519",
        "created_at": datetime.now(UTC).isoformat(),
        "certificate": {
            "filename": certificate_path.name,
            "sha256": hashlib.sha256(certificate).hexdigest(),
            "size_bytes": len(certificate),
        },
        "public_key": {
            "encoding": "raw-base64",
            "value": base64.b64encode(public_raw).decode("ascii"),
            "fingerprint_sha256": _fingerprint(public_raw),
        },
        "signature": {
            "encoding": "base64",
            "value": base64.b64encode(private_key.sign(_DOMAIN + certificate)).decode("ascii"),
        },
    }
    signature_path.parent.mkdir(parents=True, exist_ok=True)
    _write_bytes_atomic(
        signature_path,
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        mode=0o644,
    )
    return payload


def verify_certificate_signature(
    certificate_path: Path,
    signature_path: Path,
    trusted_public_key_path: Path,
    artifact_dir: Path | None = None,
) -> list[str]:
    certificate_errors = verify_certificate_file(certificate_path, artifact_dir)
    errors = [f"certificate: {error}" for error in certificate_errors]
    try:
        payload = json.loads(signature_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return errors + [f"signature envelope cannot be read: {error}"]
    if not isinstance(payload, dict):
        return errors + ["signature envelope must be a JSON object"]
    schema_errors = sorted(
        _SIGNATURE_VALIDATOR.iter_errors(payload),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
    )
    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"signature schema violation at {location}: {error.message}")
    if schema_errors:
        return errors

    certificate = certificate_path.read_bytes()
    descriptor = payload["certificate"]
    assert isinstance(descriptor, dict)
    if descriptor["filename"] != certificate_path.name:
        errors.append("signature certificate filename does not match")
    if descriptor["size_bytes"] != len(certificate):
        errors.append("signature certificate size does not match")
    if descriptor["sha256"] != hashlib.sha256(certificate).hexdigest():
        errors.append("signature certificate checksum does not match")

    try:
        embedded_raw = base64.b64decode(payload["public_key"]["value"], validate=True)
        signature = base64.b64decode(payload["signature"]["value"], validate=True)
    except (binascii.Error, ValueError, TypeError) as error:
        return errors + [f"signature envelope contains invalid base64: {error}"]
    if payload["public_key"]["fingerprint_sha256"] != _fingerprint(embedded_raw):
        errors.append("embedded public key fingerprint does not match")

    try:
        embedded_key = Ed25519PublicKey.from_public_bytes(embedded_raw)
    except ValueError as error:
        return errors + [f"embedded public key is invalid: {error}"]
    try:
        trusted_key = _load_public_key(trusted_public_key_path)
    except (OSError, ValueError) as error:
        return errors + [f"trusted public key cannot be loaded: {error}"]
    if _raw_public_key(trusted_key) != embedded_raw:
        errors.append("signer public key does not match the trusted public key")
    try:
        embedded_key.verify(signature, _DOMAIN + certificate)
    except InvalidSignature:
        errors.append("Ed25519 signature is invalid")
    return errors


def password_from_environment(variable: str) -> bytes:
    value = os.environ.get(variable)
    if value is None:
        raise ValueError(f"password environment variable is not set: {variable}")
    password = value.encode("utf-8")
    _validate_password(password)
    return password


def _load_private_key(path: Path, password: bytes) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=password)
    except (OSError, ValueError, TypeError) as error:
        raise ValueError(f"encrypted private key cannot be loaded: {error}") from error
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("private key is not Ed25519")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("trusted public key is not Ed25519")
    return key


def _raw_public_key(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _fingerprint(raw_public_key: bytes) -> str:
    return hashlib.sha256(raw_public_key).hexdigest()


def _validate_password(password: bytes) -> None:
    if len(password) < 12:
        raise ValueError("key password must contain at least 12 UTF-8 bytes")


def _require_private_permissions(path: Path) -> None:
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise ValueError("private key permissions are too open; expected mode 0600")


def _write_bytes_atomic(path: Path, content: bytes, *, mode: int) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
