from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .claims import extract_claims
from .ml_contracts import canonical_contract_json
from .ml_features import sparse_text_features, tfidf_vector


MODEL_SCHEMA = "reprocheck.sparse-logistic-claim-model.v1"


@dataclass(frozen=True)
class SparseLogisticModel:
    schema_version: str
    corpus_sha256: str
    split_sha256: str
    seed: int
    feature_names: tuple[str, ...]
    inverse_document_frequency: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    decision_threshold: float
    training_example_count: int
    training_owner_count: int
    training_data_sha256: str
    epochs: int
    learning_rate: float
    l2: float
    model_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "corpus_sha256": self.corpus_sha256,
            "split_sha256": self.split_sha256,
            "seed": self.seed,
            "feature_names": list(self.feature_names),
            "inverse_document_frequency": list(self.inverse_document_frequency),
            "coefficients": list(self.coefficients),
            "intercept": self.intercept,
            "decision_threshold": self.decision_threshold,
            "training_example_count": self.training_example_count,
            "training_owner_count": self.training_owner_count,
            "training_data_sha256": self.training_data_sha256,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "model_sha256": self.model_sha256,
        }


def rule_claim_candidate(text: str) -> bool:
    return bool(extract_claims(text))


def _digest(payload: dict[str, Any], field: str) -> str:
    value = dict(payload)
    value[field] = ""
    return hashlib.sha256(canonical_contract_json(value).encode("utf-8")).hexdigest()


def _validate_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def train_sparse_logistic(
    examples: list[dict[str, object]],
    *,
    corpus_sha256: str,
    split_sha256: str,
    seed: int,
    epochs: int = 200,
    learning_rate: float = 0.8,
    l2: float = 0.001,
    maximum_features: int = 20_000,
) -> SparseLogisticModel:
    _validate_sha256(corpus_sha256, "corpus_sha256")
    _validate_sha256(split_sha256, "split_sha256")
    if epochs < 1 or not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("epochs and learning_rate must be positive")
    if not math.isfinite(l2) or l2 < 0 or maximum_features < 1:
        raise ValueError("l2 must be nonnegative and maximum_features must be positive")
    if len(examples) < 2:
        raise ValueError("training requires at least two examples")
    block_ids: set[str] = set()
    labels: list[bool] = []
    texts: list[str] = []
    owners: set[str] = set()
    normalized_rows: list[dict[str, object]] = []
    for row in examples:
        required = {"block_id", "owner_id", "text", "label", "split"}
        if set(row) != required:
            raise ValueError("training examples must contain the exact declared fields")
        if row["split"] != "train":
            raise ValueError("all examples must belong to the training split")
        block_id, owner_id, text = str(row["block_id"]), str(row["owner_id"]), str(row["text"])
        if not block_id or block_id in block_ids:
            raise ValueError("training block_id values must be non-empty and unique")
        if not owner_id or not text:
            raise ValueError("training owner_id and text must be non-empty")
        if not isinstance(row["label"], bool):
            raise ValueError("training labels must be boolean")
        block_ids.add(block_id)
        owners.add(owner_id)
        labels.append(row["label"])
        texts.append(text)
        normalized_rows.append(
            {"block_id": block_id, "owner_id": owner_id, "text": text, "label": row["label"]}
        )
    if len(set(labels)) != 2:
        raise ValueError("training data must contain two classes")

    feature_counts = [sparse_text_features(text) for text in texts]
    document_frequency: Counter[str] = Counter()
    for values in feature_counts:
        document_frequency.update(values.keys())
    selected = sorted(document_frequency, key=lambda name: (-document_frequency[name], name))[
        :maximum_features
    ]
    feature_names = tuple(sorted(selected))
    vocabulary = {name: index for index, name in enumerate(feature_names)}
    sample_count = len(texts)
    idf = tuple(
        math.log((1 + sample_count) / (1 + document_frequency[name])) + 1 for name in feature_names
    )
    vectors = [tfidf_vector(text, vocabulary, idf) for text in texts]
    weights = [0.0] * len(feature_names)
    intercept = 0.0
    order = sorted(range(sample_count), key=lambda index: (str(examples[index]["block_id"]), index))
    for _ in range(epochs):
        gradient = [0.0] * len(weights)
        intercept_gradient = 0.0
        for index in order:
            score = intercept + sum(
                weights[position] * value for position, value in vectors[index].items()
            )
            probability = _sigmoid(score)
            error = probability - float(labels[index])
            intercept_gradient += error
            for position, value in vectors[index].items():
                gradient[position] += error * value
        scale = 1 / sample_count
        for position in range(len(weights)):
            weights[position] -= learning_rate * (
                gradient[position] * scale + l2 * weights[position]
            )
        intercept -= learning_rate * intercept_gradient * scale

    training_digest = hashlib.sha256(
        canonical_contract_json(
            sorted(normalized_rows, key=lambda row: str(row["block_id"]))
        ).encode("utf-8")
    ).hexdigest()
    model = SparseLogisticModel(
        schema_version=MODEL_SCHEMA,
        corpus_sha256=corpus_sha256,
        split_sha256=split_sha256,
        seed=seed,
        feature_names=feature_names,
        inverse_document_frequency=idf,
        coefficients=tuple(weights),
        intercept=intercept,
        decision_threshold=0.5,
        training_example_count=sample_count,
        training_owner_count=len(owners),
        training_data_sha256=training_digest,
        epochs=epochs,
        learning_rate=learning_rate,
        l2=l2,
        model_sha256="",
    )
    return replace(model, model_sha256=_digest(model.to_dict(), "model_sha256"))


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1 / (1 + inverse)
    exponent = math.exp(value)
    return exponent / (1 + exponent)


def predict_claim_probability(model: SparseLogisticModel, text: str) -> float:
    vocabulary = {name: index for index, name in enumerate(model.feature_names)}
    vector = tfidf_vector(text, vocabulary, model.inverse_document_frequency)
    score = model.intercept + sum(
        model.coefficients[index] * value for index, value in vector.items()
    )
    return _sigmoid(score)


def write_sparse_logistic_model(model: SparseLogisticModel, path: Path) -> None:
    if path.exists():
        raise ValueError(f"model output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_contract_json(model.to_dict()) + "\n", encoding="utf-8")


def load_sparse_logistic_model(path: Path) -> SparseLogisticModel:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load sparse logistic model: {path}") from error
    required = set(SparseLogisticModel.__dataclass_fields__)
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("sparse logistic model has unexpected or missing fields")
    if payload["schema_version"] != MODEL_SCHEMA:
        raise ValueError("unsupported sparse logistic model schema")
    for name in ("corpus_sha256", "split_sha256", "training_data_sha256", "model_sha256"):
        _validate_sha256(str(payload[name]), name)
    feature_names = tuple(str(value) for value in payload["feature_names"])
    idf = tuple(float(value) for value in payload["inverse_document_frequency"])
    coefficients = tuple(float(value) for value in payload["coefficients"])
    if (
        not feature_names
        or len(feature_names) != len(idf)
        or len(feature_names) != len(coefficients)
    ):
        raise ValueError("sparse logistic model feature arrays have inconsistent lengths")
    numeric = (
        *idf,
        *coefficients,
        float(payload["intercept"]),
        float(payload["decision_threshold"]),
    )
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("sparse logistic model values must be finite")
    if _digest(payload, "model_sha256") != payload["model_sha256"]:
        raise ValueError("sparse logistic model digest does not match")
    return SparseLogisticModel(
        schema_version=payload["schema_version"],
        corpus_sha256=payload["corpus_sha256"],
        split_sha256=payload["split_sha256"],
        seed=int(payload["seed"]),
        feature_names=feature_names,
        inverse_document_frequency=idf,
        coefficients=coefficients,
        intercept=float(payload["intercept"]),
        decision_threshold=float(payload["decision_threshold"]),
        training_example_count=int(payload["training_example_count"]),
        training_owner_count=int(payload["training_owner_count"]),
        training_data_sha256=payload["training_data_sha256"],
        epochs=int(payload["epochs"]),
        learning_rate=float(payload["learning_rate"]),
        l2=float(payload["l2"]),
        model_sha256=payload["model_sha256"],
    )
