from __future__ import annotations

import json
from pathlib import Path

import pytest

from reprocheck.ml_baselines import (
    load_sparse_logistic_model,
    predict_claim_probability,
    rule_claim_candidate,
    train_sparse_logistic,
    write_sparse_logistic_model,
)


def _examples() -> list[dict[str, object]]:
    positives = [
        "Accuracy reached 94% on the test set.",
        "The model achieved an F1 score of 0.87.",
        "AUROC: 0.91 for the held-out cohort.",
        "Точность модели составила 92% на тестовой выборке.",
        "Сынақ жиынындағы F1 көрсеткіші 0.84 болды.",
        "Validation Dice improved to 0.89.",
    ]
    negatives = [
        "Version 2.1 was released in 2025.",
        "The batch size was 64 and learning rate was 0.001.",
        "The model contains 120 million parameters.",
        "Жоба 2024 жылы басталды және 3 нұсқасы бар.",
        "Оқыту 50 эпоха бойы жүргізілді.",
        "See reference 12 on page 94.",
    ]
    rows: list[dict[str, object]] = []
    for label, values in ((True, positives), (False, negatives)):
        for index, text in enumerate(values):
            rows.append(
                {
                    "block_id": f"{'p' if label else 'n'}-{index}",
                    "owner_id": f"owner-{'p' if label else 'n'}-{index // 2}",
                    "text": text,
                    "label": label,
                    "split": "train",
                }
            )
    return rows


def test_rule_baseline_uses_frozen_claim_parser() -> None:
    assert rule_claim_candidate("Accuracy: 94%") is True
    assert rule_claim_candidate("Version 2.1 was released") is False


def test_sparse_logistic_training_is_deterministic_and_predictive() -> None:
    first = train_sparse_logistic(
        _examples(), corpus_sha256="a" * 64, split_sha256="b" * 64, seed=17, epochs=300
    )
    second = train_sparse_logistic(
        _examples(), corpus_sha256="a" * 64, split_sha256="b" * 64, seed=17, epochs=300
    )
    assert first.to_dict() == second.to_dict()
    positive = predict_claim_probability(first, "Test accuracy was 0.96.")
    negative = predict_claim_probability(first, "Training used 100 epochs and batch size 32.")
    assert 0 <= negative < positive <= 1
    assert first.training_example_count == 12
    assert first.training_owner_count == 6


def test_model_round_trip_is_hash_bound_and_rejects_overwrite(tmp_path: Path) -> None:
    model = train_sparse_logistic(
        _examples(), corpus_sha256="a" * 64, split_sha256="b" * 64, seed=5, epochs=50
    )
    path = tmp_path / "model.json"
    write_sparse_logistic_model(model, path)
    loaded = load_sparse_logistic_model(path)
    assert loaded == model
    with pytest.raises(ValueError, match="already exists"):
        write_sparse_logistic_model(model, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["coefficients"][0] += 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        load_sparse_logistic_model(path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda rows: rows[0].update(split="test"), "training split"),
        (lambda rows: rows[1].update(block_id=rows[0]["block_id"]), "block_id"),
        (lambda rows: [row.update(label=True) for row in rows], "two classes"),
        (lambda rows: rows[0].update(label=1), "boolean"),
    ],
)
def test_training_rejects_leaky_or_malformed_examples(mutation, message: str) -> None:
    examples = _examples()
    mutation(examples)
    with pytest.raises(ValueError, match=message):
        train_sparse_logistic(examples, corpus_sha256="a" * 64, split_sha256="b" * 64, seed=1)
