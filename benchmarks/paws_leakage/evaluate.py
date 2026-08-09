from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

from reprocheck.leakage import text_similarity
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "source-manifest.json"
METHODS = (
    "normalized_exact",
    "token_jaccard",
    "character_trigram_dice",
    "hybrid_lexical_v1",
    "ordered_tokens_v1",
    "sequence_char_v1",
    "tfidf_word_1_2",
    "tfidf_char_wb_3_5",
    "logistic_lexical_features_v1",
)
LOGISTIC_FEATURES = (
    "token_jaccard",
    "character_trigram_dice",
    "hybrid_lexical_v1",
    "ordered_tokens_v1",
    "sequence_char_v1",
    "tfidf_word_1_2",
    "tfidf_char_wb_3_5",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", " ", value)


def _character_ngrams(value: str, size: int = 3) -> set[str]:
    normalized = re.sub(r"[^\w]+", " ", _normalize(value), flags=re.UNICODE).strip()
    padded = f" {normalized} "
    return {padded[index : index + size] for index in range(max(0, len(padded) - size + 1))}


def _character_dice(left: str, right: str) -> float:
    left_ngrams = _character_ngrams(left)
    right_ngrams = _character_ngrams(right)
    total = len(left_ngrams) + len(right_ngrams)
    return 2 * len(left_ngrams & right_ngrams) / total if total else 0.0


def _load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError(
            "install the benchmark extra: pip install 'reprocheck[benchmark]'"
        ) from error
    rows = parquet.read_table(path, columns=["id", "sentence1", "sentence2", "label"]).to_pylist()
    if not rows or any(row["label"] not in (0, 1) for row in rows):
        raise ValueError("PAWS source has invalid or empty labels")
    identifiers = [row["id"] for row in rows]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("PAWS source contains duplicate pair identifiers")
    return rows


def _pair_scores(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    pairs = [(str(row["sentence1"]), str(row["sentence2"])) for row in rows]
    scores: dict[str, list[float]] = {
        "normalized_exact": [float(_normalize(left) == _normalize(right)) for left, right in pairs],
        "token_jaccard": [text_similarity(left, right, "token_jaccard") for left, right in pairs],
        "character_trigram_dice": [_character_dice(left, right) for left, right in pairs],
        "hybrid_lexical_v1": [
            text_similarity(left, right, "hybrid_lexical_v1") for left, right in pairs
        ],
        "ordered_tokens_v1": [
            text_similarity(left, right, "ordered_tokens_v1") for left, right in pairs
        ],
        "sequence_char_v1": [
            difflib.SequenceMatcher(
                None, _normalize(left), _normalize(right), autojunk=False
            ).ratio()
            for left, right in pairs
        ],
    }
    return scores


def _tfidf_scores(
    development_rows: list[dict[str, Any]], evaluation_rows: list[dict[str, Any]]
) -> dict[str, list[float]]:
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError as error:
        raise RuntimeError(
            "install the benchmark extra: pip install 'reprocheck[benchmark]'"
        ) from error

    development_texts = [
        str(row[field]) for row in development_rows for field in ("sentence1", "sentence2")
    ]
    evaluation_left = [str(row["sentence1"]) for row in evaluation_rows]
    evaluation_right = [str(row["sentence2"]) for row in evaluation_rows]
    configurations = {
        "tfidf_word_1_2": {
            "analyzer": "word",
            "ngram_range": (1, 2),
            "token_pattern": r"(?u)\b\w+\b",
        },
        "tfidf_char_wb_3_5": {"analyzer": "char_wb", "ngram_range": (3, 5)},
    }
    output: dict[str, list[float]] = {}
    for method, options in configurations.items():
        vectorizer = TfidfVectorizer(lowercase=True, norm="l2", dtype=np.float64, **options)
        vectorizer.fit(development_texts)
        left_matrix = vectorizer.transform(evaluation_left)
        right_matrix = vectorizer.transform(evaluation_right)
        output[method] = np.asarray(left_matrix.multiply(right_matrix).sum(axis=1)).ravel().tolist()
    return output


def _logistic_scores(
    development_rows: list[dict[str, Any]],
    evaluation_rows: list[dict[str, Any]],
    development_scores: dict[str, list[float]],
    evaluation_scores: dict[str, list[float]],
    *,
    development_phase: bool,
) -> list[float]:
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedKFold, cross_val_predict
    except ImportError as error:
        raise RuntimeError(
            "install the benchmark extra: pip install 'reprocheck[benchmark]'"
        ) from error

    development_matrix = np.column_stack(
        [development_scores[feature] for feature in LOGISTIC_FEATURES]
    )
    development_labels = np.asarray([int(row["label"]) for row in development_rows])

    def model() -> LogisticRegression:
        return LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=1000,
            random_state=20260809,
            solver="liblinear",
        )

    if development_phase:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=20260809)
        probabilities = cross_val_predict(
            model(), development_matrix, development_labels, cv=folds, method="predict_proba"
        )[:, 1]
    else:
        fitted = model().fit(development_matrix, development_labels)
        evaluation_matrix = np.column_stack(
            [evaluation_scores[feature] for feature in LOGISTIC_FEATURES]
        )
        probabilities = fitted.predict_proba(evaluation_matrix)[:, 1]
    return probabilities.tolist()


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 1.0]
    estimate = successes / total
    denominator = 1 + z * z / total
    center = (estimate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(estimate * (1 - estimate) / total + z * z / (4 * total**2))
    return [center - margin / denominator, center + margin / denominator]


def _metrics(labels: list[int], scores: list[float], threshold: float) -> dict[str, Any]:
    predicted = [int(score >= threshold) for score in scores]
    tp = sum(label == prediction == 1 for label, prediction in zip(labels, predicted))
    tn = sum(label == prediction == 0 for label, prediction in zip(labels, predicted))
    fp = sum(label == 0 and prediction == 1 for label, prediction in zip(labels, predicted))
    fn = sum(label == 1 and prediction == 0 for label, prediction in zip(labels, predicted))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": (tp + tn) / len(labels),
        "balanced_accuracy": (recall + specificity) / 2,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "precision_wilson_95": _wilson(tp, tp + fp),
        "recall_wilson_95": _wilson(tp, tp + fn),
        "specificity_wilson_95": _wilson(tn, tn + fp),
    }


def _choose_threshold(labels: list[int], scores: list[float]) -> dict[str, Any]:
    candidates = (_metrics(labels, scores, step / 1000) for step in range(1, 1001))
    return max(
        candidates,
        key=lambda result: (
            result["balanced_accuracy"],
            result["f1"],
            result["threshold"],
        ),
    )


def _mcnemar_exact(labels: list[int], left: list[int], right: list[int]) -> dict[str, Any]:
    left_only = sum(
        left_prediction == label and right_prediction != label
        for label, left_prediction, right_prediction in zip(labels, left, right)
    )
    right_only = sum(
        right_prediction == label and left_prediction != label
        for label, left_prediction, right_prediction in zip(labels, left, right)
    )
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, index) for index in range(min(left_only, right_only) + 1))
        p_value = min(1.0, 2 * tail / 2**discordant)
    return {
        "left_only_correct": left_only,
        "right_only_correct": right_only,
        "discordant": discordant,
        "exact_two_sided_p": p_value,
    }


def evaluate(
    source: Path,
    development_source: Path,
    phase: str,
    thresholds: dict[str, float] | None,
) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["files"][phase]
    if source.stat().st_size != expected["bytes"] or _sha256(source) != expected["sha256"]:
        raise ValueError(f"PAWS {phase} source does not match the locked manifest")
    development_expected = manifest["files"]["validation"]
    if _sha256(development_source) != development_expected["sha256"]:
        raise ValueError("PAWS development source does not match the locked manifest")

    rows = _load_rows(source)
    if len(rows) != expected["rows"]:
        raise ValueError(f"PAWS {phase} source has an unexpected row count")
    development_rows = rows if phase == "validation" else _load_rows(development_source)
    if len(development_rows) != development_expected["rows"]:
        raise ValueError("PAWS development source has an unexpected row count")
    labels = [int(row["label"]) for row in rows]
    scores = _pair_scores(rows)
    scores.update(_tfidf_scores(development_rows, rows))
    if phase == "validation":
        development_scores = scores
    else:
        development_scores = _pair_scores(development_rows)
        development_scores.update(_tfidf_scores(development_rows, development_rows))
    scores["logistic_lexical_features_v1"] = _logistic_scores(
        development_rows,
        rows,
        development_scores,
        scores,
        development_phase=phase == "validation",
    )
    if set(scores) != set(METHODS):
        raise AssertionError("benchmark method set is incomplete")

    results = {
        method: _choose_threshold(labels, values)
        if thresholds is None
        else _metrics(labels, values, thresholds[method])
        for method, values in scores.items()
    }
    predictions = {
        method: [int(score >= results[method]["threshold"]) for score in values]
        for method, values in scores.items()
    }
    comparisons = {
        "ordered_tokens_v1_vs_hybrid_lexical_v1": _mcnemar_exact(
            labels, predictions["ordered_tokens_v1"], predictions["hybrid_lexical_v1"]
        ),
        "tfidf_char_wb_3_5_vs_hybrid_lexical_v1": _mcnemar_exact(
            labels, predictions["tfidf_char_wb_3_5"], predictions["hybrid_lexical_v1"]
        ),
    }
    return {
        "schema": "reprocheck.paws-leakage-study.v1",
        "tool_version": __version__,
        "phase": "development_threshold_selection" if phase == "validation" else "locked_test",
        "dataset": {
            "name": manifest["dataset"],
            "split": phase,
            "source_sha256": _sha256(source),
            "rows": len(rows),
            "positive": sum(labels),
            "negative": len(labels) - sum(labels),
            "independent_human_labels": True,
        },
        "threshold_selection": {
            "source_split": "validation",
            "objective": "maximum balanced accuracy on a fixed 0.001 grid",
            "test_labels_used_for_thresholds": False,
        },
        "methods": results,
        "paired_comparisons": comparisons,
        "interpretation_boundary": manifest["limitations"],
    }


def _load_thresholds(path: Path) -> dict[str, float]:
    registration = json.loads(path.read_text(encoding="utf-8"))
    thresholds = registration.get("frozen_thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != set(METHODS):
        raise ValueError("preregistration does not freeze every benchmark threshold")
    return {method: float(value) for method, value in thresholds.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["validation", "test"], required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--development-source", type=Path)
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "test" and not args.preregistration:
        parser.error("--preregistration is required for the locked test phase")
    development_source = args.development_source or args.source
    thresholds = _load_thresholds(args.preregistration) if args.preregistration else None
    if args.phase == "test" and args.output.exists():
        raise FileExistsError("refusing to overwrite the one-shot locked test output")
    result = evaluate(args.source, development_source, args.phase, thresholds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for method in METHODS:
        metrics = result["methods"][method]
        print(
            f"{method}: threshold={metrics['threshold']:.3f} "
            f"balanced_accuracy={metrics['balanced_accuracy']:.2%} "
            f"precision={metrics['precision']:.2%} recall={metrics['recall']:.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
