from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from reprocheck.ml_dataset import load_ml_dataset, validate_ml_dataset


def _descriptor(path: Path, artifact_id: str) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "artifact_id": artifact_id,
        "path": path.name,
        "role": "report",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def _payload(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    first = tmp_path / "alpha.md"
    second = tmp_path / "beta.md"
    first.write_text("Accuracy reached 0.94 on test.", encoding="utf-8")
    second.write_text("Version 2.1 was released.", encoding="utf-8")
    corpus: dict[str, Any] = {
        "schema_version": "reprocheck.ml-corpus.v1",
        "corpus_id": "fixture-v1",
        "created_at": "2026-08-21T00:00:00Z",
        "repositories": [
            {
                "repository_id": "repo-alpha",
                "owner_id": "owner-alpha",
                "commit_sha": "a" * 40,
                "source_url": "https://example.test/alpha",
                "retrieved_at": "2026-08-20T00:00:00Z",
                "license": "MIT",
                "domain": "vision",
                "language": "en",
                "lineage_id": "lineage-alpha",
                "is_fork": False,
                "artifacts": [_descriptor(first, "artifact-alpha")],
            },
            {
                "repository_id": "repo-beta",
                "owner_id": "owner-beta",
                "commit_sha": "b" * 40,
                "source_url": "https://example.test/beta",
                "retrieved_at": "2026-08-20T00:00:00Z",
                "license": "Apache-2.0",
                "domain": "nlp",
                "language": "en",
                "lineage_id": "lineage-beta",
                "is_fork": False,
                "artifacts": [_descriptor(second, "artifact-beta")],
            },
        ],
    }
    annotations: dict[str, Any] = {
        "schema_version": "reprocheck.ml-annotations.v1",
        "corpus_id": "fixture-v1",
        "blocks": [
            {
                "block_id": "block-alpha",
                "repository_id": "repo-alpha",
                "artifact_id": "artifact-alpha",
                "source_start": 0,
                "source_end": len(first.read_text(encoding="utf-8")),
                "raw_text": first.read_text(encoding="utf-8"),
                "normalized_text": "accuracy reached 0.94 on test.",
                "block_type": "prose",
                "language": "en",
                "lineage_id": "block-lineage-alpha",
                "contains_eligible_claim": True,
                "review_status": "agreed",
                "claims": [
                    {
                        "claim_id": "claim-alpha",
                        "metric": "accuracy",
                        "value": 0.94,
                        "unit": "scalar",
                        "metric_span": [0, 8],
                        "value_span": [17, 21],
                        "context": {"split": "test"},
                    }
                ],
            },
            {
                "block_id": "block-beta",
                "repository_id": "repo-beta",
                "artifact_id": "artifact-beta",
                "source_start": 0,
                "source_end": len(second.read_text(encoding="utf-8")),
                "raw_text": second.read_text(encoding="utf-8"),
                "normalized_text": "version 2.1 was released.",
                "block_type": "prose",
                "language": "en",
                "lineage_id": "block-lineage-beta",
                "contains_eligible_claim": False,
                "review_status": "primary_only",
                "claims": [],
            },
        ],
        "evidence_pairs": [],
    }
    return corpus, annotations


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_dataset_loads_provenance_bound_claims(tmp_path: Path) -> None:
    corpus, annotations = _payload(tmp_path)
    result = load_ml_dataset(
        _write(tmp_path / "corpus.json", corpus),
        _write(tmp_path / "annotations.json", annotations),
        sources_root=tmp_path,
    )
    assert result.corpus_id == "fixture-v1"
    assert result.repository_count == 2
    assert result.block_count == 2
    assert result.claim_count == 1
    assert len(result.dataset_sha256) == 64


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda c, a: c.update(unexpected=True), "additional properties"),
        (
            lambda c, a: c["repositories"][1].update(owner_id="owner-alpha"),
            "one repository per owner",
        ),
        (lambda c, a: c["repositories"][0].update(is_fork=True), "fork"),
        (
            lambda c, a: a["blocks"][0].update(review_status="unresolved"),
            "unresolved",
        ),
        (
            lambda c, a: a["blocks"][0]["claims"][0].update(value=float("nan")),
            "finite",
        ),
        (
            lambda c, a: a["blocks"][0]["claims"][0].update(value_span=[0, 8]),
            "numeric source",
        ),
    ],
)
def test_dataset_rejects_invalid_or_unreviewed_records(
    tmp_path: Path, mutation, message: str
) -> None:
    corpus, annotations = _payload(tmp_path)
    mutation(corpus, annotations)
    with pytest.raises(ValueError, match=message):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)


def test_dataset_rejects_tampered_or_escaping_artifacts(tmp_path: Path) -> None:
    corpus, annotations = _payload(tmp_path)
    corpus["repositories"][0]["artifacts"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)

    corpus, annotations = _payload(tmp_path)
    corpus["repositories"][0]["artifacts"][0]["path"] = "../alpha.md"
    with pytest.raises(ValueError, match="safe relative path"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)


def test_dataset_digest_changes_with_annotation_but_not_mapping_order(tmp_path: Path) -> None:
    corpus, annotations = _payload(tmp_path)
    original = validate_ml_dataset(corpus, annotations, sources_root=tmp_path)
    reordered = validate_ml_dataset(
        json.loads(json.dumps(corpus, sort_keys=True)),
        json.loads(json.dumps(annotations, sort_keys=True)),
        sources_root=tmp_path,
    )
    changed_annotations = copy.deepcopy(annotations)
    changed_annotations["blocks"][1]["language"] = "ru"
    changed = validate_ml_dataset(corpus, changed_annotations, sources_root=tmp_path)
    assert original.dataset_sha256 == reordered.dataset_sha256
    assert original.dataset_sha256 != changed.dataset_sha256


def test_dataset_loader_rejects_unreadable_and_nonobject_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_ml_dataset(bad, bad, sources_root=tmp_path)
    with pytest.raises(ValueError, match="cannot load"):
        load_ml_dataset(tmp_path / "missing", bad, sources_root=tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda c, a: c["repositories"][1].update(repository_id="repo-alpha"),
            "repository_id values",
        ),
        (
            lambda c, a: c["repositories"][0]["artifacts"].append(
                copy.deepcopy(c["repositories"][0]["artifacts"][0])
            ),
            "artifact_id values",
        ),
        (
            lambda c, a: c["repositories"][0]["artifacts"][0].update(size_bytes=1),
            "size does not match",
        ),
        (
            lambda c, a: a["blocks"][1].update(block_id="block-alpha"),
            "block_id values",
        ),
        (
            lambda c, a: a["blocks"][0].update(artifact_id="missing"),
            "unknown artifact",
        ),
        (
            lambda c, a: a["blocks"][0].update(source_end=1),
            "source range",
        ),
        (
            lambda c, a: a["blocks"][0].update(normalized_text="wrong"),
            "normalized_text",
        ),
        (
            lambda c, a: a["blocks"][0].update(contains_eligible_claim=False),
            "claim presence",
        ),
        (
            lambda c, a: a["blocks"][0].update(review_status="primary_only"),
            "positive annotation",
        ),
        (
            lambda c, a: a["blocks"][1].update(
                contains_eligible_claim=True,
                review_status="agreed",
                claims=[copy.deepcopy(a["blocks"][0]["claims"][0])],
            ),
            "claim_id values",
        ),
    ],
)
def test_dataset_custom_integrity_guards(tmp_path: Path, mutation, message: str) -> None:
    corpus, annotations = _payload(tmp_path)
    mutation(corpus, annotations)
    with pytest.raises(ValueError, match=message):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)


def test_dataset_rejects_missing_and_non_utf8_annotated_artifacts(tmp_path: Path) -> None:
    corpus, annotations = _payload(tmp_path)
    (tmp_path / "alpha.md").unlink()
    with pytest.raises(ValueError, match="artifact is missing"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)

    corpus, annotations = _payload(tmp_path)
    path = tmp_path / "alpha.md"
    path.write_bytes(b"\xff\xfe")
    corpus["repositories"][0]["artifacts"][0] = _descriptor(path, "artifact-alpha")
    with pytest.raises(ValueError, match="UTF-8"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)


@pytest.mark.parametrize(
    ("pair", "message"),
    [
        (
            {
                "claim_id": "claim-alpha",
                "repository_id": "repo-alpha",
                "artifact_id": "artifact-alpha",
                "label": "compatible",
                "review_status": "unresolved",
            },
            "unresolved",
        ),
        (
            {
                "claim_id": "missing",
                "repository_id": "repo-alpha",
                "artifact_id": "artifact-alpha",
                "label": "incompatible",
                "review_status": "agreed",
            },
            "unknown claim",
        ),
        (
            {
                "claim_id": "claim-alpha",
                "repository_id": "repo-alpha",
                "artifact_id": "missing",
                "label": "incompatible",
                "review_status": "agreed",
            },
            "unknown artifact",
        ),
        (
            {
                "claim_id": "claim-alpha",
                "repository_id": "repo-beta",
                "artifact_id": "artifact-beta",
                "label": "compatible",
                "review_status": "agreed",
            },
            "claim repository",
        ),
    ],
)
def test_dataset_evidence_pair_guards(
    tmp_path: Path, pair: dict[str, object], message: str
) -> None:
    corpus, annotations = _payload(tmp_path)
    annotations["evidence_pairs"] = [pair]
    with pytest.raises(ValueError, match=message):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)


def test_dataset_rejects_mismatched_corpus_id_unresolved_negative_and_symlink_escape(
    tmp_path: Path,
) -> None:
    corpus, annotations = _payload(tmp_path)
    annotations["corpus_id"] = "other"
    with pytest.raises(ValueError, match="different corpus_id"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)

    corpus, annotations = _payload(tmp_path)
    annotations["blocks"][1]["review_status"] = "unresolved"
    with pytest.raises(ValueError, match="annotation is unresolved"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)

    outside = tmp_path.parent / f"outside-{tmp_path.name}.md"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "linked.md"
    link.symlink_to(outside)
    corpus, annotations = _payload(tmp_path)
    corpus["repositories"][0]["artifacts"][0] = _descriptor(link, "artifact-alpha")
    with pytest.raises(ValueError, match="safe relative path"):
        validate_ml_dataset(corpus, annotations, sources_root=tmp_path)
