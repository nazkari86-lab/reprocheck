from __future__ import annotations

from pathlib import Path

import pytest

from reprocheck.ml_transformer import (
    TransformerConfig,
    load_transformer_manifest,
    predict_transformer,
    train_transformer,
)


class FixtureRuntime:
    def train(self, rows, output_dir: Path, config):  # type: ignore[no-untyped-def]
        (output_dir / "model.safetensors").write_bytes(b"safe-fixture")
        (output_dir / "config.json").write_text("{}\n", encoding="utf-8")
        return {"torch": "fixture", "transformers": "fixture"}

    def predict(self, model_dir: Path, texts, config):  # type: ignore[no-untyped-def]
        assert (model_dir / "model.safetensors").is_file()
        return [0.91 if "точность" in text else 0.51 for text in texts]


def rows() -> list[dict[str, object]]:
    return [
        {
            "block_id": "b-1",
            "owner_id": "alice",
            "text": "Accuracy reached 91%.",
            "label": True,
            "language": "en",
            "split": "train",
        },
        {
            "block_id": "b-2",
            "owner_id": "bolat",
            "text": "Бұл кіріспе мәтін.",
            "label": False,
            "language": "kk",
            "split": "train",
        },
    ]


def test_fixture_runtime_freezes_and_verifies_model(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    manifest = train_transformer(
        rows(),
        model_dir,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        runtime=FixtureRuntime(),
    )
    assert manifest["training_owner_count"] == 2
    assert load_transformer_manifest(model_dir) == manifest

    predictions = predict_transformer(
        model_dir,
        ["точность 91%", "no number"],
        ["ru", "xx"],
        runtime=FixtureRuntime(),
    )
    assert predictions[0].predicted_label is True
    assert predictions[0].out_of_distribution is False
    assert predictions[1].language == "other"
    assert predictions[1].out_of_distribution is True


def test_manifest_rejects_tampered_model(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    train_transformer(
        rows(),
        model_dir,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        runtime=FixtureRuntime(),
    )
    (model_dir / "model.safetensors").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="file mismatch"):
        load_transformer_manifest(model_dir)


def test_training_rejects_non_train_rows_before_runtime(tmp_path: Path) -> None:
    invalid = rows()
    invalid[0] = {**invalid[0], "split": "validation"}
    with pytest.raises(ValueError, match="only training-split"):
        train_transformer(
            invalid,
            tmp_path / "model",
            corpus_sha256="a" * 64,
            split_sha256="b" * 64,
            runtime=FixtureRuntime(),
        )


def test_config_rejects_unpinned_revision() -> None:
    with pytest.raises(ValueError, match="exact 40-character"):
        TransformerConfig(revision="main")
