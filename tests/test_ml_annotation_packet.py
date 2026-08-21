from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from reprocheck.ml_annotation_packet import (
    build_annotation_packets,
    compare_annotation_reviews,
    write_annotation_packets,
)


def _fixture(tmp_path: Path):  # type: ignore[no-untyped-def]
    path = tmp_path / "sources" / "repo" / "README.md"
    path.parent.mkdir(parents=True)
    text = "Accuracy reached 94% on test.\n\nInstall with Python 3.12.\n\nTiny."
    path.write_text(text, encoding="utf-8")
    data = path.read_bytes()
    corpus = {
        "corpus_id": "fixture",
        "repositories": [{
            "repository_id": "owner/repo",
            "artifacts": [{
                "artifact_id": "owner/repo:README.md",
                "path": "sources/repo/README.md",
                "sha256": hashlib.sha256(data).hexdigest(),
            }],
        }],
    }
    return corpus, text


def test_packets_are_deterministic_blinded_and_independently_ordered(tmp_path: Path) -> None:
    corpus, _ = _fixture(tmp_path)
    a, b, mapping = build_annotation_packets(corpus, sources_root=tmp_path, seed=7)
    again = build_annotation_packets(corpus, sources_root=tmp_path, seed=7)
    assert (a, b, mapping) == again
    assert mapping["candidate_count"] == 1
    assert mapping["sampled_negative_count"] == 1
    assert {row["blind_id"] for row in a["blocks"]} == {row["blind_id"] for row in b["blocks"]}
    assert [row["blind_id"] for row in a["blocks"]] != [row["blind_id"] for row in b["blocks"]]
    assert all("repository_id" not in row for row in a["blocks"])
    assert all(row["contains_eligible_claim"] is None for row in a["blocks"])


def test_packet_writer_and_guards(tmp_path: Path) -> None:
    corpus, _ = _fixture(tmp_path)
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
    output = tmp_path / "packet"
    assert write_annotation_packets(corpus_path, tmp_path, output, seed=7)["blocks"] == 2
    assert (output / "reviewer-a.json").is_file()
    with pytest.raises(ValueError, match="already exists"):
        write_annotation_packets(corpus_path, tmp_path, output, seed=7)
    with pytest.raises(ValueError, match="character limits"):
        build_annotation_packets(corpus, sources_root=tmp_path, seed=1, minimum_characters=0)
    with pytest.raises(ValueError, match="negative_ratio"):
        build_annotation_packets(corpus, sources_root=tmp_path, seed=1, negative_ratio=6)
    with pytest.raises(ValueError, match="no repositories"):
        build_annotation_packets({"repositories": []}, sources_root=tmp_path, seed=1)
    corpus["repositories"][0]["artifacts"][0]["sha256"] = "bad"
    with pytest.raises(ValueError, match="checksum"):
        build_annotation_packets(corpus, sources_root=tmp_path, seed=1)
    corpus["repositories"][0]["artifacts"][0]["path"] = "../escape"
    with pytest.raises(ValueError, match="unsafe artifact path"):
        build_annotation_packets(corpus, sources_root=tmp_path, seed=1)


def test_review_comparison_requires_complete_independent_exact_labels(tmp_path: Path) -> None:
    corpus, _ = _fixture(tmp_path)
    a, b, mapping = build_annotation_packets(corpus, sources_root=tmp_path, seed=7)
    for packet in (a, b):
        for row in packet["blocks"]:
            row["contains_eligible_claim"] = False
    result = compare_annotation_reviews(a, b, mapping)
    assert result["agreement_count"] == 2
    assert result["exact_agreement"] == 1
    b["blocks"][0]["contains_eligible_claim"] = True
    b["blocks"][0]["claims"] = [{"metric": "accuracy"}]
    result = compare_annotation_reviews(a, b, mapping)
    assert result["disagreement_count"] == 1
    assert result["adjudication_queue"][0]["adjudicated_label"] is None


def test_review_comparison_rejects_invalid_packets(tmp_path: Path) -> None:
    corpus, _ = _fixture(tmp_path)
    a, b, mapping = build_annotation_packets(corpus, sources_root=tmp_path, seed=7)
    with pytest.raises(ValueError, match="incomplete"):
        compare_annotation_reviews(a, b, mapping)
    b["mapping_sha256"] = "bad"
    with pytest.raises(ValueError, match="different mappings"):
        compare_annotation_reviews(a, b, mapping)
    b["mapping_sha256"] = a["mapping_sha256"]
    b["reviewer"] = a["reviewer"]
    with pytest.raises(ValueError, match="distinct reviewer"):
        compare_annotation_reviews(a, b, mapping)
    b["reviewer"] = "other"
    mapping["seed"] = 9
    with pytest.raises(ValueError, match="digest is invalid"):
        compare_annotation_reviews(a, b, mapping)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda packet: packet.update(blocks=None), "blocks must be an array"),
        (lambda packet: packet["blocks"].append(packet["blocks"][0]), "duplicate blocks"),
        (lambda packet: packet["blocks"].pop(), "complete mapping"),
        (lambda packet: packet["blocks"][0].update(claims=None), "claims must be an array"),
        (
            lambda packet: packet["blocks"][0].update(contains_eligible_claim=True),
            "decision disagrees",
        ),
    ],
)
def test_review_comparison_packet_structure_guards(tmp_path: Path, mutation, message: str) -> None:  # type: ignore[no-untyped-def]
    corpus, _ = _fixture(tmp_path)
    a, b, mapping = build_annotation_packets(corpus, sources_root=tmp_path, seed=7)
    for packet in (a, b):
        for row in packet["blocks"]:
            row["contains_eligible_claim"] = False
    mutation(b)
    with pytest.raises(ValueError, match=message):
        compare_annotation_reviews(a, b, mapping)
