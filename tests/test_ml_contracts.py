from __future__ import annotations

import json
import math

import pytest

from reprocheck.ml_contracts import (
    EvidenceCandidate,
    MLClaimTuple,
    ModelScores,
    SelectiveThresholds,
    canonical_contract_json,
)


def _claim(**changes: object) -> MLClaimTuple:
    values: dict[str, object] = {
        "claim_id": "claim-001",
        "metric": "accuracy",
        "value": 0.94,
        "unit": "scalar",
        "source_text": "Accuracy reached 0.94 on the hidden test split.",
        "metric_span": (0, 8),
        "value_span": (17, 21),
        "context": {"split": "test", "model": "baseline"},
    }
    values.update(changes)
    return MLClaimTuple(**values)  # type: ignore[arg-type]


def test_claim_tuple_binds_values_and_context_to_source() -> None:
    claim = _claim()
    assert claim.metric_text == "Accuracy"
    assert claim.value_text == "0.94"
    assert claim.context == {"model": "baseline", "split": "test"}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"value": math.nan}, "finite"),
        ({"metric_span": (8, 0)}, "metric_span"),
        ({"value_span": (17, 99)}, "value_span"),
        ({"value_span": (0, 8)}, "numeric source"),
        ({"value": 0.42}, "does not match"),
        ({"context": {"owner": "secret"}}, "unsupported context"),
        ({"context": {"split": "  "}}, "non-empty"),
    ],
)
def test_claim_tuple_rejects_unbound_or_unsafe_values(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _claim(**changes)


def test_evidence_candidate_and_scores_are_strictly_bounded() -> None:
    candidate = EvidenceCandidate(
        candidate_id="evidence-001",
        artifact_id="predictions.csv",
        evidence_grade="raw_recomputed",
        metric="accuracy",
        value=None,
        context={"model": "baseline", "split": "test"},
        rank_score=0.98,
        rank_margin=0.41,
        integrity_verified=True,
    )
    scores = ModelScores(
        claim_probability=0.97,
        tuple_probability=0.96,
        evidence_probability=0.98,
        out_of_distribution_score=0.03,
        rule_agreement=True,
    )
    assert candidate.evidence_grade == "raw_recomputed"
    assert scores.claim_probability == 0.97

    with pytest.raises(ValueError, match="between 0 and 1"):
        ModelScores(
            claim_probability=1.1,
            tuple_probability=0.5,
            evidence_probability=0.5,
            out_of_distribution_score=0.5,
            rule_agreement=False,
        )
    with pytest.raises(ValueError, match="rank_margin"):
        EvidenceCandidate(
            candidate_id="e",
            artifact_id="a",
            evidence_grade="structured_reported",
            metric="f1",
            value=0.8,
            context={},
            rank_score=0.8,
            rank_margin=-0.1,
            integrity_verified=True,
        )


def test_thresholds_reject_inverted_review_and_verify_bands() -> None:
    with pytest.raises(ValueError, match="review threshold"):
        SelectiveThresholds(
            verify_claim_probability=0.8,
            verify_tuple_probability=0.8,
            verify_evidence_probability=0.8,
            review_claim_probability=0.9,
            review_tuple_probability=0.4,
            review_evidence_probability=0.4,
            minimum_completeness=0.8,
            minimum_rank_margin=0.1,
            maximum_ood_score=0.2,
        )


def test_contract_json_is_canonical_and_non_finite_safe() -> None:
    claim = _claim()
    first = canonical_contract_json({"claim": claim, "z": 1})
    second = canonical_contract_json({"z": 1, "claim": claim})
    assert first == second
    assert json.loads(first)["claim"]["claim_id"] == "claim-001"
    with pytest.raises(ValueError, match="finite"):
        canonical_contract_json({"bad": float("inf")})
