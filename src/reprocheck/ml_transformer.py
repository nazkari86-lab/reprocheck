from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from .ml_contracts import canonical_contract_json


MODEL_SCHEMA = "reprocheck.multilingual-claim-model.v1"
DEFAULT_ENCODER = "intfloat/multilingual-e5-small"
DEFAULT_REVISION = "d1d99a1efae6779390caba937d92c54b5bc70e51"
SUPPORTED_LANGUAGES = ("en", "ru", "kk")


@dataclass(frozen=True)
class TransformerConfig:
    encoder: str = DEFAULT_ENCODER
    revision: str = DEFAULT_REVISION
    max_length: int = 256
    seed: int = 1729
    epochs: int = 3
    learning_rate: float = 2e-5
    batch_size: int = 8
    weight_decay: float = 0.01
    ood_confidence_threshold: float = 0.60

    def __post_init__(self) -> None:
        if not self.encoder or len(self.revision) != 40:
            raise ValueError("encoder and exact 40-character revision are required")
        if self.max_length < 8 or self.epochs < 1 or self.batch_size < 1:
            raise ValueError("max_length, epochs, and batch_size must be positive")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive and finite")
        if not math.isfinite(self.weight_decay) or self.weight_decay < 0:
            raise ValueError("weight_decay must be nonnegative and finite")
        if not 0 < self.ood_confidence_threshold <= 1:
            raise ValueError("ood_confidence_threshold must be in (0, 1]")


@dataclass(frozen=True)
class TransformerPrediction:
    probability: float
    predicted_label: bool
    confidence: float
    out_of_distribution: bool
    language: str

    def __post_init__(self) -> None:
        for value in (self.probability, self.confidence):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("prediction probabilities must be finite and in [0, 1]")
        if self.language not in (*SUPPORTED_LANGUAGES, "other"):
            raise ValueError("language must be en, ru, kk, or other")


class TransformerRuntime(Protocol):
    def train(
        self, rows: Sequence[dict[str, object]], output_dir: Path, config: TransformerConfig
    ) -> dict[str, str]: ...

    def predict(
        self, model_dir: Path, texts: Sequence[str], config: TransformerConfig
    ) -> list[float]: ...


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_ml_dependencies() -> tuple[Any, Any]:  # pragma: no cover - optional runtime
    try:
        import torch
        import transformers
    except ImportError as error:
        raise RuntimeError("transformer support requires: pip install 'reprocheck[ml]'") from error
    return torch, transformers


def _set_determinism(torch: Any, seed: int) -> None:  # pragma: no cover - optional runtime
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if hasattr(torch, "use_deterministic_algorithms"):
        torch.use_deterministic_algorithms(True, warn_only=True)


class HuggingFaceRuntime:
    def train(  # pragma: no cover - exercised only with the optional pinned runtime
        self, rows: Sequence[dict[str, object]], output_dir: Path, config: TransformerConfig
    ) -> dict[str, str]:
        torch, transformers = _require_ml_dependencies()
        _set_determinism(torch, config.seed)
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            config.encoder, revision=config.revision
        )
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            config.encoder, revision=config.revision, num_labels=2
        )
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
        )
        ordered = sorted(rows, key=lambda row: str(row["block_id"]))
        model.train()
        for _ in range(config.epochs):
            for start in range(0, len(ordered), config.batch_size):
                batch = ordered[start : start + config.batch_size]
                encoded = tokenizer(
                    [str(row["text"]) for row in batch],
                    padding=True,
                    truncation=True,
                    max_length=config.max_length,
                    return_tensors="pt",
                )
                labels = torch.tensor([int(bool(row["label"])) for row in batch])
                optimizer.zero_grad(set_to_none=True)
                loss = model(**encoded, labels=labels).loss
                loss.backward()
                optimizer.step()
        model.eval()
        model.save_pretrained(output_dir, safe_serialization=True)
        tokenizer.save_pretrained(output_dir)
        return {
            "torch": str(torch.__version__),
            "transformers": str(transformers.__version__),
        }

    def predict(  # pragma: no cover - exercised only with the optional pinned runtime
        self, model_dir: Path, texts: Sequence[str], config: TransformerConfig
    ) -> list[float]:
        torch, transformers = _require_ml_dependencies()
        _set_determinism(torch, config.seed)
        tokenizer = transformers.AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            model_dir, local_files_only=True, use_safetensors=True
        )
        model.eval()
        probabilities: list[float] = []
        with torch.inference_mode():
            for start in range(0, len(texts), config.batch_size):
                encoded = tokenizer(
                    list(texts[start : start + config.batch_size]),
                    padding=True,
                    truncation=True,
                    max_length=config.max_length,
                    return_tensors="pt",
                )
                values = torch.softmax(model(**encoded).logits, dim=-1)[:, 1].tolist()
                probabilities.extend(float(value) for value in values)
        return probabilities


def _validate_training_rows(rows: Sequence[dict[str, object]]) -> tuple[int, str]:
    if len(rows) < 2:
        raise ValueError("transformer training requires at least two examples")
    owners: set[str] = set()
    labels: set[bool] = set()
    normalized: list[dict[str, object]] = []
    block_ids: set[str] = set()
    for row in rows:
        if set(row) != {"block_id", "owner_id", "text", "label", "language", "split"}:
            raise ValueError("transformer rows must contain the exact declared fields")
        if row["split"] != "train":
            raise ValueError("transformer training accepts only training-split rows")
        block_id = str(row["block_id"])
        owner = str(row["owner_id"])
        language = str(row["language"])
        if not block_id or block_id in block_ids or not owner or not str(row["text"]):
            raise ValueError("block ids must be unique and text/owner must be non-empty")
        if language not in SUPPORTED_LANGUAGES or not isinstance(row["label"], bool):
            raise ValueError("labels must be boolean and language must be en, ru, or kk")
        block_ids.add(block_id)
        owners.add(owner)
        labels.add(row["label"])
        normalized.append({key: row[key] for key in sorted(row) if key != "split"})
    if len(labels) != 2:
        raise ValueError("transformer training data must contain two classes")
    digest = hashlib.sha256(
        canonical_contract_json(sorted(normalized, key=lambda row: str(row["block_id"]))).encode()
    ).hexdigest()
    return len(owners), digest


def train_transformer(
    rows: Sequence[dict[str, object]],
    output_dir: Path,
    *,
    corpus_sha256: str,
    split_sha256: str,
    config: TransformerConfig = TransformerConfig(),
    runtime: TransformerRuntime | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise ValueError(f"model output already exists: {output_dir}")
    for name, value in (("corpus_sha256", corpus_sha256), ("split_sha256", split_sha256)):
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    owner_count, training_digest = _validate_training_rows(rows)
    output_dir.mkdir(parents=True)
    try:
        versions = (runtime or HuggingFaceRuntime()).train(rows, output_dir, config)
        files = {
            path.relative_to(output_dir).as_posix(): _sha256(path)
            for path in sorted(output_dir.rglob("*"))
            if path.is_file()
        }
        if not files:
            raise ValueError("transformer runtime produced no model files")
        manifest: dict[str, Any] = {
            "schema_version": MODEL_SCHEMA,
            "encoder": config.encoder,
            "revision": config.revision,
            "config": asdict(config),
            "corpus_sha256": corpus_sha256,
            "split_sha256": split_sha256,
            "training_data_sha256": training_digest,
            "training_example_count": len(rows),
            "training_owner_count": owner_count,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                **dict(sorted(versions.items())),
            },
            "files": files,
            "manifest_sha256": "",
        }
        manifest["manifest_sha256"] = hashlib.sha256(
            canonical_contract_json(manifest).encode()
        ).hexdigest()
        (output_dir / "reprocheck-model-manifest.json").write_text(
            canonical_contract_json(manifest) + "\n", encoding="utf-8"
        )
        return manifest
    except Exception:
        # Keep failed runs inspectable, but never mistake them for a valid frozen model.
        (output_dir / "TRAINING_FAILED").write_text(
            f"python={sys.version.split()[0]}\n", encoding="utf-8"
        )
        raise


def load_transformer_manifest(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "reprocheck-model-manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load transformer manifest: {path}") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MODEL_SCHEMA:
        raise ValueError("unsupported transformer manifest")
    expected = str(manifest.get("manifest_sha256", ""))
    unsigned = {**manifest, "manifest_sha256": ""}
    if hashlib.sha256(canonical_contract_json(unsigned).encode()).hexdigest() != expected:
        raise ValueError("transformer manifest digest mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("transformer manifest contains no files")
    for relative, digest in files.items():
        target = (model_dir / str(relative)).resolve()
        try:
            target.relative_to(model_dir.resolve())
        except ValueError as error:
            raise ValueError("transformer manifest contains an unsafe path") from error
        if not target.is_file() or _sha256(target) != digest:
            raise ValueError(f"transformer model file mismatch: {relative}")
    return manifest


def predict_transformer(
    model_dir: Path,
    texts: Sequence[str],
    languages: Sequence[str],
    *,
    runtime: TransformerRuntime | None = None,
) -> list[TransformerPrediction]:
    if len(texts) != len(languages):
        raise ValueError("texts and languages must have equal length")
    manifest = load_transformer_manifest(model_dir)
    config = TransformerConfig(**manifest["config"])
    probabilities = (runtime or HuggingFaceRuntime()).predict(model_dir, texts, config)
    if len(probabilities) != len(texts):
        raise ValueError("transformer runtime returned the wrong prediction count")
    results: list[TransformerPrediction] = []
    for probability, language in zip(probabilities, languages):
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("transformer runtime returned an invalid probability")
        normalized_language = language if language in SUPPORTED_LANGUAGES else "other"
        confidence = max(probability, 1 - probability)
        results.append(
            TransformerPrediction(
                probability=probability,
                predicted_label=probability >= 0.5,
                confidence=confidence,
                out_of_distribution=(
                    normalized_language == "other" or confidence < config.ood_confidence_threshold
                ),
                language=normalized_language,
            )
        )
    return results
