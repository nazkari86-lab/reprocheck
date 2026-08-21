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


class EmptyRuntime(FixtureRuntime):
    def train(self, rows, output_dir: Path, config):  # type: ignore[no-untyped-def]
        return {}


class BadPredictionRuntime(FixtureRuntime):
    probabilities: list[float] = []

    def predict(self, model_dir: Path, texts, config):  # type: ignore[no-untyped-def]
        return self.probabilities


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


@pytest.mark.parametrize(
    "changes",
    [
        {"max_length": 1},
        {"epochs": 0},
        {"batch_size": 0},
        {"learning_rate": 0},
        {"weight_decay": -1},
        {"ood_confidence_threshold": 0},
    ],
)
def test_config_rejects_invalid_hyperparameters(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        TransformerConfig(**changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda values: values.pop(), "at least two"),
        (lambda values: values[0].update(extra=True), "exact declared"),
        (lambda values: values[1].update(block_id="b-1"), "unique"),
        (lambda values: values[0].update(language="de"), "language"),
        (lambda values: values[0].update(label=1), "boolean"),
        (lambda values: values[0].update(label=False), "two classes"),
    ],
)
def test_training_row_contract_rejects_malformed_data(
    tmp_path: Path, mutation, message: str
) -> None:
    values = rows()
    mutation(values)
    with pytest.raises(ValueError, match=message):
        train_transformer(
            values,
            tmp_path / "model",
            corpus_sha256="a" * 64,
            split_sha256="b" * 64,
            runtime=FixtureRuntime(),
        )


def test_transformer_failure_manifest_digest_and_prediction_guards(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        train_transformer(rows(), tmp_path / "bad-digest", corpus_sha256="x", split_sha256="b" * 64)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        train_transformer(rows(), existing, corpus_sha256="a" * 64, split_sha256="b" * 64)
    failed = tmp_path / "failed"
    with pytest.raises(ValueError, match="no model files"):
        train_transformer(
            rows(),
            failed,
            corpus_sha256="a" * 64,
            split_sha256="b" * 64,
            runtime=EmptyRuntime(),
        )
    assert (failed / "TRAINING_FAILED").is_file()

    model_dir = tmp_path / "model"
    train_transformer(
        rows(),
        model_dir,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        runtime=FixtureRuntime(),
    )
    with pytest.raises(ValueError, match="equal length"):
        predict_transformer(model_dir, ["one"], [], runtime=FixtureRuntime())
    bad = BadPredictionRuntime()
    bad.probabilities = []
    with pytest.raises(ValueError, match="wrong prediction count"):
        predict_transformer(model_dir, ["one"], ["en"], runtime=bad)
    bad.probabilities = [float("nan")]
    with pytest.raises(ValueError, match="invalid probability"):
        predict_transformer(model_dir, ["one"], ["en"], runtime=bad)


def test_manifest_rejects_missing_unsupported_empty_and_unsafe(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot load"):
        load_transformer_manifest(tmp_path / "missing")
    model_dir = tmp_path / "model"
    train_transformer(
        rows(),
        model_dir,
        corpus_sha256="a" * 64,
        split_sha256="b" * 64,
        runtime=FixtureRuntime(),
    )
    manifest_path = model_dir / "reprocheck-model-manifest.json"
    import json
    import hashlib
    from reprocheck.ml_contracts import canonical_contract_json

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "bad"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_transformer_manifest(model_dir)

    payload["schema_version"] = "reprocheck.multilingual-claim-model.v1"
    payload["files"] = {}
    payload["manifest_sha256"] = ""
    payload["manifest_sha256"] = hashlib.sha256(
        canonical_contract_json(payload).encode()
    ).hexdigest()
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="no files"):
        load_transformer_manifest(model_dir)

    payload["files"] = {"../outside": "0" * 64}
    payload["manifest_sha256"] = ""
    payload["manifest_sha256"] = hashlib.sha256(
        canonical_contract_json(payload).encode()
    ).hexdigest()
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        load_transformer_manifest(model_dir)

    payload["files"] = {"model.safetensors": "0" * 64}
    payload["manifest_sha256"] = "bad"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest digest"):
        load_transformer_manifest(model_dir)
