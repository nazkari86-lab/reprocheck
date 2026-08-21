from __future__ import annotations

import copy

import pytest

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


def test_candidate_and_ranking_contract_guards() -> None:
    malformed = _artifacts()[0]
    malformed.pop("metric_names")
    with pytest.raises(ValueError, match="exact declared"):
        generate_evidence_candidates(_claim(), [malformed])
    duplicate = _artifacts()[0]
    with pytest.raises(ValueError, match="unique"):
        generate_evidence_candidates(_claim(), [duplicate, copy.deepcopy(duplicate)])
    with pytest.raises(ValueError, match="unique claim_id"):
        score_evidence_ranking(
            [
                {"claim_id": "a", "expected_artifact_id": "x", "ranked_artifact_ids": []},
                {"claim_id": "a", "expected_artifact_id": "y", "ranked_artifact_ids": []},
            ]
        )
    assert score_evidence_ranking([]) == {
        "claims": 0,
        "recall_at_1": 0.0,
        "recall_at_3": 0.0,
        "mrr": 0.0,
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda pair: pair.update(extra=True), "exact declared"),
        (lambda pair: pair.update(split="test"), "training split"),
        (lambda pair: pair.update(claim="bad"), "MLClaimTuple"),
        (lambda pair: pair.update(artifact="bad"), "artifact must be an object"),
        (lambda pair: pair.update(label=1), "labels must be boolean"),
    ],
)
def test_ranker_rejects_malformed_pairs(mutation, message: str) -> None:
    pair: dict[str, object] = {
        "claim": _claim(),
        "artifact": _artifacts()[0],
        "label": True,
        "hard_negative": False,
        "split": "train",
    }
    mutation(pair)
    with pytest.raises(ValueError, match=message):
        train_evidence_ranker([pair], corpus_sha256="a" * 64, split_sha256="b" * 64)


def test_ranker_rejects_digests_parameters_single_class_and_feature_mismatch() -> None:
    pair = {
        "claim": _claim(),
        "artifact": _artifacts()[0],
        "label": True,
        "hard_negative": False,
        "split": "train",
    }
    with pytest.raises(ValueError, match="SHA-256"):
        train_evidence_ranker([pair], corpus_sha256="bad", split_sha256="b" * 64)
    with pytest.raises(ValueError, match="parameters"):
        train_evidence_ranker([], corpus_sha256="a" * 64, split_sha256="b" * 64)
    with pytest.raises(ValueError, match="positive and negative"):
        train_evidence_ranker([pair], corpus_sha256="a" * 64, split_sha256="b" * 64)

    training = []
    for artifact, label in zip(_artifacts()[:2], (True, False)):
        training.append({**pair, "artifact": artifact, "label": label})
    model = train_evidence_ranker(training, corpus_sha256="a" * 64, split_sha256="b" * 64, epochs=1)
    object.__setattr__(model, "feature_names", ("bad",))
    with pytest.raises(ValueError, match="feature contract"):
        rank_evidence_candidates(
            model, _claim(), generate_evidence_candidates(_claim(), _artifacts())
        )
