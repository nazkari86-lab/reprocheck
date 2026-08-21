from __future__ import annotations

import pytest

from reprocheck.ml_mutation_experiment import (
    build_numeric_mutation_pairs,
    numeric_consistency,
    run_numeric_mutation_experiment,
)


def _fixtures():  # type: ignore[no-untyped-def]
    repositories, blocks = [], []
    for domain in ("cv", "nlp"):
        for index in range(9):
            repository_id = f"{domain}/repo-{index}"
            repositories.append(
                {
                    "repository_id": repository_id,
                    "owner_id": f"owner-{domain}-{index}",
                    "domain": domain,
                    "lineage_id": repository_id,
                }
            )
            blocks.append(
                {
                    "blind_id": f"B-{domain}-{index}",
                    "repository_id": repository_id,
                    "raw_text": f"{domain} accuracy {80 + index}% and recall {70 + index}%",
                    "metric_hint": True,
                    "numeric_hint": True,
                }
            )
    return {"repositories": repositories}, {"blocks": blocks}


def test_numeric_mutations_are_balanced_local_and_reproducible() -> None:
    corpus, mapping = _fixtures()
    rows, split = build_numeric_mutation_pairs(corpus, mapping, seed=8)
    assert len(rows) == 36
    assert sum(row["label"] for row in rows) == 18
    assert (rows, split) == build_numeric_mutation_pairs(corpus, mapping, seed=8)
    for positive, negative in zip(rows[::2], rows[1::2]):
        assert positive["claim_text"] == positive["evidence_text"]
        assert negative["claim_text"] != negative["evidence_text"]
        assert positive["repository_id"] == negative["repository_id"]


def test_mutation_experiment_trains_and_reports_hybrid_ablation() -> None:
    corpus, mapping = _fixtures()
    rows, split = build_numeric_mutation_pairs(corpus, mapping, seed=8)
    report, model = run_numeric_mutation_experiment(
        rows, split, corpus_sha256="b" * 64, seed=8, bootstrap_samples=20
    )
    assert report["status"] == "auxiliary_constructed_not_human_gold"
    assert set(report["results"]) == {"text_only", "hybrid_numeric", "lexical_overlap"}
    assert report["results"]["hybrid_numeric"]["test_owner_bootstrap_95"]["samples"] == 20
    assert report["results"]["hybrid_numeric"]["test"]["f1"] > report["results"]["text_only"]["test"]["f1"]
    assert len(model["model_sha256"]) == 64


def test_numeric_consistency_handles_missing_partial_and_full_values() -> None:
    assert numeric_consistency("no number", "accuracy 1") == 0
    assert numeric_consistency("accuracy 1 recall 2", "accuracy 1 recall 3") == 0.5
    assert numeric_consistency("accuracy 1", "accuracy 1") == 1
    corpus, mapping = _fixtures()
    for block in mapping["blocks"]:
        block["raw_text"] = "accuracy 1"
    with pytest.raises(ValueError, match="distinct values"):
        build_numeric_mutation_pairs(corpus, mapping, seed=8)
