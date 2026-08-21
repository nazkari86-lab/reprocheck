from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from typing import Any, Callable

from .ml_baselines import predict_claim_probability, train_sparse_logistic
from .ml_contracts import canonical_contract_json
from .ml_split import build_owner_disjoint_split


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in text.split() if len(token) > 1}


def lexical_overlap(claim: str, evidence: str) -> float:
    left, right = _tokens(claim), _tokens(evidence)
    return len(left & right) / len(left | right) if left or right else 0.0


def build_silver_pairs(
    corpus: dict[str, Any], mapping: dict[str, Any], *, seed: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    repositories = [
        {
            "repository_id": item["repository_id"],
            "owner_id": item["owner_id"],
            "domain": item["domain"],
            "lineage_id": item["lineage_id"],
        }
        for item in corpus["repositories"]
    ]
    repository_by_id = {item["repository_id"]: item for item in repositories}
    candidates = [item for item in mapping["blocks"] if item["metric_hint"] and item["numeric_hint"]]
    blocks = [
        {
            "block_id": item["blind_id"],
            "repository_id": item["repository_id"],
            "lineage_id": item["blind_id"],
            "raw_text": item["raw_text"],
        }
        for item in candidates
    ]
    split = build_owner_disjoint_split(repositories, blocks, seed=seed)
    split_by_repository = {
        repository_id: name
        for name, repository_ids in split["splits"].items()
        for repository_id in repository_ids
    }
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        repository = repository_by_id[item["repository_id"]]
        grouped[(split_by_repository[item["repository_id"]], repository["domain"])].append(item)
    for values in grouped.values():
        values.sort(key=lambda item: item["blind_id"])
        if len({item["repository_id"] for item in values}) < 2:
            raise ValueError("silver pairing needs two candidate repositories per split and domain")

    rows: list[dict[str, Any]] = []
    rng = random.Random(seed)
    for item in sorted(candidates, key=lambda value: value["blind_id"]):
        repository = repository_by_id[item["repository_id"]]
        split_name = split_by_repository[item["repository_id"]]
        alternatives = [
            value
            for value in grouped[(split_name, repository["domain"])]
            if value["repository_id"] != item["repository_id"]
        ]
        negative = alternatives[rng.randrange(len(alternatives))]
        for label, evidence, evidence_repository in (
            (True, item["raw_text"], item["repository_id"]),
            (False, negative["raw_text"], negative["repository_id"]),
        ):
            rows.append(
                {
                    "pair_id": f"{item['blind_id']}:{'positive' if label else 'negative'}",
                    "claim_id": item["blind_id"],
                    "repository_id": item["repository_id"],
                    "owner_id": repository["owner_id"],
                    "evidence_repository_id": evidence_repository,
                    "domain": repository["domain"],
                    "split": split_name,
                    "claim_text": item["raw_text"],
                    "evidence_text": evidence,
                    "label": label,
                }
            )
    return rows, split


def _auc(labels: list[bool], scores: list[float]) -> float:
    positives = [score for score, label in zip(scores, labels) if label]
    negatives = [score for score, label in zip(scores, labels) if not label]
    if not positives or not negatives:
        return 0.0
    wins = sum((left > right) + 0.5 * (left == right) for left in positives for right in negatives)
    return wins / (len(positives) * len(negatives))


def _metrics(labels: list[bool], scores: list[float], threshold: float) -> dict[str, float | int]:
    predicted = [score >= threshold for score in scores]
    tp = sum(actual and guess for actual, guess in zip(labels, predicted))
    fp = sum(not actual and guess for actual, guess in zip(labels, predicted))
    fn = sum(actual and not guess for actual, guess in zip(labels, predicted))
    tn = len(labels) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    brier = sum((score - float(label)) ** 2 for score, label in zip(scores, labels)) / len(labels)
    return {
        "records": len(labels),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auroc": _auc(labels, scores),
        "brier": brier,
        "threshold": threshold,
    }


def _best_threshold(labels: list[bool], scores: list[float]) -> float:
    candidates = sorted({0.0, 0.5, 1.0, *scores})
    return max(candidates, key=lambda value: (_metrics(labels, scores, value)["f1"], value))


def _bootstrap(
    rows: list[dict[str, Any]], scores: list[float], threshold: float, *, seed: int, samples: int
) -> dict[str, Any]:
    by_owner: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_owner[row["owner_id"]].append(index)
    owners = sorted(by_owner)
    rng = random.Random(seed)
    f1_values: list[float] = []
    auc_values: list[float] = []
    for _ in range(samples):
        selected = [rng.choice(owners) for _ in owners]
        indices = [index for owner in selected for index in by_owner[owner]]
        labels = [bool(rows[index]["label"]) for index in indices]
        values = [scores[index] for index in indices]
        f1_values.append(float(_metrics(labels, values, threshold)["f1"]))
        auc_values.append(_auc(labels, values))
    result: dict[str, Any] = {"samples": samples}
    for name, values in (("f1", f1_values), ("auroc", auc_values)):
        values.sort()
        result[name] = {
            "low": values[math.floor(0.025 * (samples - 1))],
            "high": values[math.ceil(0.975 * (samples - 1))],
        }
    return result


def run_silver_experiment(
    rows: list[dict[str, Any]],
    split: dict[str, Any],
    *,
    corpus_sha256: str,
    seed: int,
    bootstrap_samples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    formats: dict[str, Callable[[dict[str, Any]], str]] = {
        "full_pair": lambda row: f"claim: {row['claim_text']} evidence: {row['evidence_text']}",
        "claim_only": lambda row: str(row["claim_text"]),
        "evidence_only": lambda row: str(row["evidence_text"]),
    }
    results: dict[str, Any] = {}
    full_model: dict[str, Any] | None = None
    for name, formatter in formats.items():
        train_rows = [row for row in rows if row["split"] == "train"]
        examples = [
            {
                "block_id": row["pair_id"],
                "owner_id": row["owner_id"],
                "text": formatter(row),
                "label": row["label"],
                "split": "train",
            }
            for row in train_rows
        ]
        model = train_sparse_logistic(
            examples,
            corpus_sha256=corpus_sha256,
            split_sha256=split["split_sha256"],
            seed=seed,
            epochs=300,
            learning_rate=0.7,
            l2=0.001,
            maximum_features=12_000,
        )
        validation = [row for row in rows if row["split"] == "validation"]
        validation_scores = [predict_claim_probability(model, formatter(row)) for row in validation]
        threshold = _best_threshold([bool(row["label"]) for row in validation], validation_scores)
        test = [row for row in rows if row["split"] == "test"]
        test_scores = [predict_claim_probability(model, formatter(row)) for row in test]
        results[name] = {
            "validation": _metrics(
                [bool(row["label"]) for row in validation], validation_scores, threshold
            ),
            "test": _metrics([bool(row["label"]) for row in test], test_scores, threshold),
            "model_sha256": model.model_sha256,
        }
        if name == "full_pair":
            results[name]["test_owner_bootstrap_95"] = _bootstrap(
                test, test_scores, threshold, seed=seed, samples=bootstrap_samples
            )
            full_model = model.to_dict()

    validation = [row for row in rows if row["split"] == "validation"]
    validation_scores = [lexical_overlap(row["claim_text"], row["evidence_text"]) for row in validation]
    lexical_threshold = _best_threshold(
        [bool(row["label"]) for row in validation], validation_scores
    )
    test = [row for row in rows if row["split"] == "test"]
    test_scores = [lexical_overlap(row["claim_text"], row["evidence_text"]) for row in test]
    results["lexical_overlap"] = {
        "validation": _metrics(
            [bool(row["label"]) for row in validation], validation_scores, lexical_threshold
        ),
        "test": _metrics([bool(row["label"]) for row in test], test_scores, lexical_threshold),
    }
    report: dict[str, Any] = {
        "schema_version": "reprocheck.ml-silver-evidence-experiment.v1",
        "status": "auxiliary_silver_not_human_gold",
        "seed": seed,
        "corpus_sha256": corpus_sha256,
        "split_sha256": split["split_sha256"],
        "pair_count": len(rows),
        "owner_count": len({row["owner_id"] for row in rows}),
        "split_pair_counts": {
            name: sum(row["split"] == name for row in rows)
            for name in ("train", "validation", "test")
        },
        "results": results,
        "limitations": [
            "Labels are constructed, not independently human annotated.",
            "Positive evidence repeats the source claim block and is easier than real evidence retrieval.",
            "Results must not be reported as performance on the human gold benchmark.",
        ],
        "report_sha256": "",
    }
    report["report_sha256"] = hashlib.sha256(canonical_contract_json(report).encode()).hexdigest()
    if full_model is None:
        raise AssertionError("full-pair model was not trained")
    return report, full_model
