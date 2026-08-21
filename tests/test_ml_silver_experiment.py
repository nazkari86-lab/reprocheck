from __future__ import annotations

from reprocheck.ml_silver_experiment import (
    _auc,
    _best_threshold,
    _metrics,
    build_silver_pairs,
    lexical_overlap,
    run_silver_experiment,
)


def _fixtures():  # type: ignore[no-untyped-def]
    repositories = []
    blocks = []
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
                    "raw_text": f"{domain} model {index} accuracy {80 + index}% test result",
                    "metric_hint": True,
                    "numeric_hint": True,
                }
            )
    return {"repositories": repositories}, {"blocks": blocks}


def test_silver_pairs_are_balanced_owner_disjoint_and_reproducible() -> None:
    corpus, mapping = _fixtures()
    rows, split = build_silver_pairs(corpus, mapping, seed=7)
    assert len(rows) == 36
    assert sum(row["label"] for row in rows) == 18
    assert (rows, split) == build_silver_pairs(corpus, mapping, seed=7)
    locations = {repo: name for name, values in split["splits"].items() for repo in values}
    assert all(locations[row["repository_id"]] == locations[row["evidence_repository_id"]] for row in rows)
    assert all(
        row["repository_id"] == row["evidence_repository_id"]
        for row in rows
        if row["label"]
    )


def test_silver_experiment_trains_calibrates_and_reports_ablations() -> None:
    corpus, mapping = _fixtures()
    rows, split = build_silver_pairs(corpus, mapping, seed=7)
    report, model = run_silver_experiment(
        rows, split, corpus_sha256="a" * 64, seed=7, bootstrap_samples=20
    )
    assert report["status"] == "auxiliary_silver_not_human_gold"
    assert set(report["results"]) == {
        "full_pair",
        "claim_only",
        "evidence_only",
        "lexical_overlap",
    }
    assert report["results"]["full_pair"]["test_owner_bootstrap_95"]["samples"] == 20
    assert len(model["model_sha256"]) == 64


def test_silver_metric_helpers_cover_ties_and_empty_text() -> None:
    assert lexical_overlap("", "") == 0
    assert lexical_overlap("alpha beta", "beta gamma") == 1 / 3
    assert _auc([True, False], [0.5, 0.5]) == 0.5
    assert _auc([True], [0.5]) == 0
    metrics = _metrics([True, False], [0.9, 0.1], _best_threshold([True, False], [0.9, 0.1]))
    assert metrics["f1"] == 1
