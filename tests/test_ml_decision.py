from __future__ import annotations

from reprocheck.ml_contracts import (
    EvidenceCandidate,
    MLClaimTuple,
    ModelScores,
    SelectiveThresholds,
)
from reprocheck.ml_decision import check_evidence_compatibility, select_ml_action


def _claim(context: dict[str, str] | None = None) -> MLClaimTuple:
    return MLClaimTuple(
        claim_id="claim-001",
        metric="accuracy",
        value=0.94,
        unit="scalar",
        source_text="Accuracy reached 0.94.",
        metric_span=(0, 8),
        value_span=(17, 21),
        context=context or {"model": "alpha", "dataset": "open-set", "split": "test"},
    )


def _candidate(**changes: object) -> EvidenceCandidate:
    values: dict[str, object] = {
        "candidate_id": "evidence-001",
        "artifact_id": "predictions.csv",
        "evidence_grade": "raw_recomputed",
        "metric": "accuracy",
        "value": None,
        "context": {"model": "Alpha", "dataset": "open-set", "split": "test"},
        "rank_score": 0.98,
        "rank_margin": 0.30,
        "integrity_verified": True,
    }
    values.update(changes)
    return EvidenceCandidate(**values)  # type: ignore[arg-type]


def _scores(**changes: object) -> ModelScores:
    values: dict[str, object] = {
        "claim_probability": 0.98,
        "tuple_probability": 0.97,
        "evidence_probability": 0.96,
        "out_of_distribution_score": 0.04,
        "rule_agreement": True,
    }
    values.update(changes)
    return ModelScores(**values)  # type: ignore[arg-type]


def _thresholds() -> SelectiveThresholds:
    return SelectiveThresholds(
        verify_claim_probability=0.95,
        verify_tuple_probability=0.90,
        verify_evidence_probability=0.90,
        review_claim_probability=0.60,
        review_tuple_probability=0.50,
        review_evidence_probability=0.50,
        minimum_completeness=1.0,
        minimum_rank_margin=0.15,
        maximum_ood_score=0.20,
    )


def test_compatibility_normalizes_context_and_reports_complete_match() -> None:
    result = check_evidence_compatibility(_claim(), _candidate())
    assert result.compatible is True
    assert result.completeness == 1.0
    assert result.conflicts == ()
    assert result.missing == ()


def test_compatibility_fails_closed_on_context_conflict() -> None:
    result = check_evidence_compatibility(_claim(), _candidate(context={"split": "train"}))
    assert result.compatible is False
    assert result.conflicts == ("split",)
    assert set(result.missing) == {"dataset", "model"}


def test_high_confidence_complete_candidate_can_only_proceed_to_verifier() -> None:
    decision = select_ml_action(_claim(), _candidate(), _scores(), _thresholds())
    assert decision.action == "verify"
    assert decision.final_verdict is None
    assert decision.reasons == ("eligible_for_deterministic_verification",)


def test_conflict_or_failed_integrity_forces_abstention() -> None:
    conflict = select_ml_action(
        _claim(), _candidate(context={"split": "train"}), _scores(), _thresholds()
    )
    corrupt = select_ml_action(
        _claim(), _candidate(integrity_verified=False), _scores(), _thresholds()
    )
    assert conflict.action == "abstain"
    assert "context_conflict:split" in conflict.reasons
    assert corrupt.action == "abstain"
    assert corrupt.reasons == ("artifact_integrity_not_verified",)


def test_medium_confidence_or_incomplete_evidence_routes_to_review() -> None:
    medium = select_ml_action(
        _claim(),
        _candidate(),
        _scores(claim_probability=0.75, tuple_probability=0.70),
        _thresholds(),
    )
    incomplete = select_ml_action(
        _claim(),
        _candidate(context={"model": "alpha", "dataset": "open-set"}),
        _scores(),
        _thresholds(),
    )
    assert medium.action == "review"
    assert "below_automatic_threshold" in medium.reasons
    assert incomplete.action == "review"
    assert "incomplete_evidence:split" in incomplete.reasons


def test_low_confidence_text_only_or_ood_candidate_abstains() -> None:
    low = select_ml_action(_claim(), _candidate(), _scores(claim_probability=0.40), _thresholds())
    text_only = select_ml_action(
        _claim(), _candidate(evidence_grade="text_reported"), _scores(), _thresholds()
    )
    ood = select_ml_action(
        _claim(), _candidate(), _scores(out_of_distribution_score=0.80), _thresholds()
    )
    assert low.action == "abstain"
    assert "claim_probability_below_review_threshold" in low.reasons
    assert text_only.action == "review"
    assert "text_only_evidence" in text_only.reasons
    assert ood.action == "review"
    assert "out_of_distribution" in ood.reasons


def test_rank_ambiguity_routes_to_review_even_with_high_model_scores() -> None:
    decision = select_ml_action(_claim(), _candidate(rank_margin=0.02), _scores(), _thresholds())
    assert decision.action == "review"
    assert "ambiguous_evidence_ranking" in decision.reasons
