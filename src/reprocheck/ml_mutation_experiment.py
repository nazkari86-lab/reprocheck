from __future__ import annotations

import hashlib
import random
from typing import Any, Callable

from .ml_baselines import predict_claim_probability, train_sparse_logistic
from .ml_contracts import canonical_contract_json
from .ml_extraction import enumerate_numeric_spans
from .ml_silver_experiment import _best_threshold, _bootstrap, _metrics, lexical_overlap
from .ml_split import build_owner_disjoint_split


def _numbers(text: str) -> tuple[str, ...]:
    return tuple(span.raw_text.casefold().replace(" ", "") for span in enumerate_numeric_spans(text))


def numeric_consistency(claim: str, evidence: str) -> float:
    claim_numbers, evidence_numbers = set(_numbers(claim)), set(_numbers(evidence))
    return len(claim_numbers & evidence_numbers) / len(claim_numbers) if claim_numbers else 0.0


def build_numeric_mutation_pairs(
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
    candidates = [
        item
        for item in mapping["blocks"]
        if item["metric_hint"] and item["numeric_hint"] and _numbers(item["raw_text"])
    ]
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
    location = {
        repository_id: name
        for name, repository_ids in split["splits"].items()
        for repository_id in repository_ids
    }
    all_values = sorted({number for item in candidates for number in _numbers(item["raw_text"])})
    if len(all_values) < 2:
        raise ValueError("numeric mutation requires at least two distinct values")
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for item in sorted(candidates, key=lambda value: value["blind_id"]):
        source = item["raw_text"]
        spans = enumerate_numeric_spans(source)
        target = spans[rng.randrange(len(spans))]
        replacements = [value for value in all_values if value != target.raw_text.casefold().replace(" ", "")]
        replacement = replacements[rng.randrange(len(replacements))]
        mutated = source[: target.start] + replacement + source[target.end :]
        repository = repository_by_id[item["repository_id"]]
        for label, evidence in ((True, source), (False, mutated)):
            rows.append(
                {
                    "pair_id": f"{item['blind_id']}:{'original' if label else 'mutated'}",
                    "claim_id": item["blind_id"],
                    "repository_id": item["repository_id"],
                    "owner_id": repository["owner_id"],
                    "domain": repository["domain"],
                    "split": location[item["repository_id"]],
                    "claim_text": source,
                    "evidence_text": evidence,
                    "label": label,
                }
            )
    return rows, split


def run_numeric_mutation_experiment(
    rows: list[dict[str, Any]],
    split: dict[str, Any],
    *,
    corpus_sha256: str,
    seed: int,
    bootstrap_samples: int = 1_000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    formats: dict[str, Callable[[dict[str, Any]], str]] = {
        "text_only": lambda row: f"claim: {row['claim_text']} evidence: {row['evidence_text']}",
        "hybrid_numeric": lambda row: (
            f"numeric-consistency-{round(numeric_consistency(row['claim_text'], row['evidence_text']) * 10)} "
            f"claim: {row['claim_text']} evidence: {row['evidence_text']}"
        ),
    }
    results: dict[str, Any] = {}
    hybrid_model: dict[str, Any] | None = None
    for name, formatter in formats.items():
        training = [row for row in rows if row["split"] == "train"]
        model = train_sparse_logistic(
            [
                {
                    "block_id": row["pair_id"],
                    "owner_id": row["owner_id"],
                    "text": formatter(row),
                    "label": row["label"],
                    "split": "train",
                }
                for row in training
            ],
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
        if name == "hybrid_numeric":
            results[name]["test_owner_bootstrap_95"] = _bootstrap(
                test, test_scores, threshold, seed=seed, samples=bootstrap_samples
            )
            hybrid_model = model.to_dict()
    validation = [row for row in rows if row["split"] == "validation"]
    validation_scores = [lexical_overlap(row["claim_text"], row["evidence_text"]) for row in validation]
    threshold = _best_threshold([bool(row["label"]) for row in validation], validation_scores)
    test = [row for row in rows if row["split"] == "test"]
    test_scores = [lexical_overlap(row["claim_text"], row["evidence_text"]) for row in test]
    results["lexical_overlap"] = {
        "validation": _metrics([bool(row["label"]) for row in validation], validation_scores, threshold),
        "test": _metrics([bool(row["label"]) for row in test], test_scores, threshold),
    }
    report: dict[str, Any] = {
        "schema_version": "reprocheck.ml-numeric-mutation-experiment.v1",
        "status": "auxiliary_constructed_not_human_gold",
        "seed": seed,
        "corpus_sha256": corpus_sha256,
        "split_sha256": split["split_sha256"],
        "pair_count": len(rows),
        "owner_count": len({row["owner_id"] for row in rows}),
        "results": results,
        "limitations": [
            "Negative labels are deterministic numeric mutations, not human judgments.",
            "The hybrid feature directly measures the mutation mechanism.",
            "Results demonstrate mechanism sensitivity, not general scientific-claim accuracy.",
        ],
        "report_sha256": "",
    }
    report["report_sha256"] = hashlib.sha256(canonical_contract_json(report).encode()).hexdigest()
    if hybrid_model is None:
        raise AssertionError("hybrid model was not trained")
    return report, hybrid_model
