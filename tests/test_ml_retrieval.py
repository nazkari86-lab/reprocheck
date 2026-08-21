from __future__ import annotations

from reprocheck.ml_contracts import MLClaimTuple
from reprocheck.ml_retrieval import (
    generate_evidence_candidates,
    rank_evidence_candidates,
    score_evidence_ranking,
    train_evidence_ranker,
)


def _claim(claim_id: str = "claim-1") -> MLClaimTuple:
    return MLClaimTuple(
        claim_id=claim_id,
        metric="accuracy",
        value=0.94,
        unit="scalar",
        source_text="Accuracy reached 0.94 on test for Alpha.",
        metric_span=(0, 8),
        value_span=(17, 21),
        context={"split": "test", "model": "Alpha"},
    )


def _artifacts() -> list[dict[str, object]]:
    return [
        {
            "artifact_id": "right",
            "role": "predictions",
            "metric_names": ["accuracy", "f1"],
            "context": {"split": "test", "model": "Alpha"},
            "evidence_grade": "raw_recomputed",
            "integrity_verified": True,
        },
        {
            "artifact_id": "wrong-split",
            "role": "metrics",
            "metric_names": ["accuracy"],
            "context": {"split": "train", "model": "Alpha"},
            "evidence_grade": "structured_reported",
            "integrity_verified": True,
        },
        {
            "artifact_id": "report",
            "role": "report",
            "metric_names": [],
            "context": {},
            "evidence_grade": "text_reported",
            "integrity_verified": True,
        },
        {
            "artifact_id": "manifest",
            "role": "manifest",
            "metric_names": [],
            "context": {},
            "evidence_grade": "text_reported",
            "integrity_verified": True,
        },
    ]


def test_candidate_generation_is_complete_for_supported_artifacts() -> None:
    candidates = generate_evidence_candidates(_claim(), _artifacts())
    assert [item.artifact_id for item in candidates] == ["report", "right", "wrong-split"]
    assert next(item for item in candidates if item.artifact_id == "right").compatible is True
    assert (
        next(item for item in candidates if item.artifact_id == "wrong-split").compatible is False
    )


def test_ranker_learns_hard_context_negatives_without_deleting_candidates() -> None:
    training: list[dict[str, object]] = []
    for index in range(8):
        claim = _claim(f"claim-{index}")
        for artifact in _artifacts()[:3]:
            training.append(
                {
                    "claim": claim,
                    "artifact": artifact,
                    "label": artifact["artifact_id"] == "right",
                    "hard_negative": artifact["artifact_id"] == "wrong-split",
                    "split": "train",
                }
            )
    model = train_evidence_ranker(training, corpus_sha256="a" * 64, split_sha256="b" * 64)
    candidates = generate_evidence_candidates(_claim(), _artifacts())
    ranked = rank_evidence_candidates(model, _claim(), candidates)
    assert len(ranked) == len(candidates)
    assert ranked[0].artifact_id == "right"
    assert model.hard_negative_count == 8
    assert model.model_sha256


def test_ranking_metrics_use_claim_level_denominators() -> None:
    result = score_evidence_ranking(
        [
            {"claim_id": "a", "expected_artifact_id": "x", "ranked_artifact_ids": ["x", "y"]},
            {"claim_id": "b", "expected_artifact_id": "z", "ranked_artifact_ids": ["q", "z"]},
            {"claim_id": "c", "expected_artifact_id": "m", "ranked_artifact_ids": ["q"]},
        ]
    )
    assert result["recall_at_1"] == 1 / 3
    assert result["recall_at_3"] == 2 / 3
    assert result["mrr"] == 0.5
