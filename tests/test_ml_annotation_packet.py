from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from reprocheck.ml_annotation_packet import build_annotation_packets, write_annotation_packets


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
