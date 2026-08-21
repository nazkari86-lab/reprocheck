from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .ml_contracts import MLClaimTuple, canonical_contract_json


@dataclass(frozen=True)
class MLDataset:
    corpus_id: str
    repositories: tuple[dict[str, Any], ...]
    blocks: tuple[dict[str, Any], ...]
    evidence_pairs: tuple[dict[str, Any], ...]
    dataset_sha256: str

    @property
    def repository_count(self) -> int:
        return len(self.repositories)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def claim_count(self) -> int:
        return sum(len(block["claims"]) for block in self.blocks)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _validate_schema(payload: dict[str, Any], schema_name: str, label: str) -> None:
    resource = files("reprocheck").joinpath("schemas", schema_name)
    schema = json.loads(resource.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if errors:
        path = ".".join(str(item) for item in errors[0].absolute_path) or "root"
        raise ValueError(f"{label} schema error at {path}: {errors[0].message.casefold()}")


def _safe_path(root: Path, relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts or "." in parsed.parts:
        raise ValueError(f"artifact path must be a safe relative path: {relative}")
    target = root.joinpath(*parsed.parts).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ValueError(f"artifact path must be a safe relative path: {relative}") from error
    return target


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip()).casefold()


def load_ml_dataset(corpus_path: Path, annotations_path: Path, *, sources_root: Path) -> MLDataset:
    return validate_ml_dataset(
        _load_object(corpus_path, "ML corpus"),
        _load_object(annotations_path, "ML annotations"),
        sources_root=sources_root,
    )


def validate_ml_dataset(
    corpus: dict[str, Any], annotations: dict[str, Any], *, sources_root: Path
) -> MLDataset:
    _validate_schema(corpus, "ml-corpus-v1.schema.json", "ML corpus")
    _validate_schema(annotations, "ml-annotations-v1.schema.json", "ML annotations")
    if corpus["corpus_id"] != annotations["corpus_id"]:
        raise ValueError("ML corpus and annotations use different corpus_id values")
    root = sources_root.resolve()
    repositories = corpus["repositories"]
    repository_ids = [item["repository_id"] for item in repositories]
    owner_ids = [item["owner_id"] for item in repositories]
    if len(set(repository_ids)) != len(repository_ids):
        raise ValueError("ML corpus repository_id values must be unique")
    if len(set(owner_ids)) != len(owner_ids):
        raise ValueError("ML corpus allows one repository per owner")
    if any(item["is_fork"] for item in repositories):
        raise ValueError("fork repositories are excluded from the primary ML corpus")

    artifact_paths: dict[tuple[str, str], Path] = {}
    artifact_text: dict[tuple[str, str], str] = {}
    for repository in repositories:
        local_ids: set[str] = set()
        for artifact in repository["artifacts"]:
            artifact_id = artifact["artifact_id"]
            if artifact_id in local_ids:
                raise ValueError("artifact_id values must be unique within a repository")
            local_ids.add(artifact_id)
            path = _safe_path(root, artifact["path"])
            if not path.is_file():
                raise ValueError(f"artifact is missing: {artifact['path']}")
            data = path.read_bytes()
            if len(data) != artifact["size_bytes"]:
                raise ValueError(f"artifact size does not match: {artifact['path']}")
            if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
                raise ValueError(f"artifact checksum does not match: {artifact['path']}")
            key = (repository["repository_id"], artifact_id)
            artifact_paths[key] = path
            try:
                artifact_text[key] = data.decode("utf-8")
            except UnicodeDecodeError:
                artifact_text[key] = ""

    blocks = annotations["blocks"]
    block_ids: set[str] = set()
    claim_ids: set[str] = set()
    claim_repositories: dict[str, str] = {}
    for block in blocks:
        block_id = block["block_id"]
        if block_id in block_ids:
            raise ValueError("ML annotation block_id values must be unique")
        block_ids.add(block_id)
        key = (block["repository_id"], block["artifact_id"])
        if key not in artifact_paths:
            raise ValueError(f"annotation references an unknown artifact: {block_id}")
        source = artifact_text[key]
        if not source:
            raise ValueError(f"annotated artifact must be UTF-8 text: {block_id}")
        start, end = block["source_start"], block["source_end"]
        if end <= start or end > len(source) or source[start:end] != block["raw_text"]:
            raise ValueError(f"annotation source range does not bind raw_text: {block_id}")
        if _normalize_text(block["raw_text"]) != block["normalized_text"]:
            raise ValueError(f"normalized_text does not match raw_text: {block_id}")
        claims = block["claims"]
        if bool(claims) != block["contains_eligible_claim"]:
            raise ValueError(f"claim presence label disagrees with claims: {block_id}")
        if claims and block["review_status"] not in {"agreed", "adjudicated"}:
            raise ValueError(f"positive annotation is unresolved: {block_id}")
        if block["review_status"] == "unresolved":
            raise ValueError(f"annotation is unresolved: {block_id}")
        for claim in claims:
            if claim["claim_id"] in claim_ids:
                raise ValueError("ML annotation claim_id values must be unique")
            claim_ids.add(claim["claim_id"])
            claim_repositories[claim["claim_id"]] = block["repository_id"]
            if not math.isfinite(float(claim["value"])):
                raise ValueError("annotated claim value must be finite")
            MLClaimTuple(
                claim_id=claim["claim_id"],
                metric=claim["metric"],
                value=float(claim["value"]),
                unit=claim["unit"],
                source_text=block["raw_text"],
                metric_span=tuple(claim["metric_span"]),
                value_span=tuple(claim["value_span"]),
                context=claim["context"],
            )

    for pair in annotations["evidence_pairs"]:
        if pair["review_status"] == "unresolved":
            raise ValueError(f"evidence pair is unresolved: {pair['claim_id']}")
        if pair["claim_id"] not in claim_ids:
            raise ValueError(f"evidence pair references an unknown claim: {pair['claim_id']}")
        if (pair["repository_id"], pair["artifact_id"]) not in artifact_paths:
            raise ValueError(f"evidence pair references an unknown artifact: {pair['artifact_id']}")
        if (
            pair["label"] == "compatible"
            and pair["repository_id"] != claim_repositories[pair["claim_id"]]
        ):
            raise ValueError("compatible evidence must belong to the claim repository")

    digest_payload = {"corpus": corpus, "annotations": annotations}
    digest = hashlib.sha256(canonical_contract_json(digest_payload).encode("utf-8")).hexdigest()
    return MLDataset(
        corpus_id=corpus["corpus_id"],
        repositories=tuple(repositories),
        blocks=tuple(blocks),
        evidence_pairs=tuple(annotations["evidence_pairs"]),
        dataset_sha256=digest,
    )
