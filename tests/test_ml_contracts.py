from __future__ import annotations

import json
import math

import pytest

from reprocheck.ml_contracts import (
    CompatibilityResult,
    EvidenceCandidate,
    MLClaimTuple,
    ModelScores,
    SelectiveThresholds,
    SelectiveDecision,
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


def test_contracts_reject_every_invalid_enum_boolean_and_final_verdict() -> None:
    base = dict(
        candidate_id="e",
        artifact_id="a",
        evidence_grade="raw_recomputed",
        metric="accuracy",
        value=0.9,
        context={},
        rank_score=0.8,
        rank_margin=0.2,
        integrity_verified=True,
    )
    for changes, message in [
        ({"evidence_grade": "bad"}, "evidence_grade"),
        ({"value": math.inf}, "finite"),
        ({"integrity_verified": 1}, "boolean"),
    ]:
        with pytest.raises(ValueError, match=message):
            EvidenceCandidate(**{**base, **changes})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="rule_agreement"):
        ModelScores(0.5, 0.5, 0.5, 0.5, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="compatibility"):
        CompatibilityResult(True, 1.0, (), (), ("conflict",))
    compatible = CompatibilityResult(True, 1.0, (), (), ())
    with pytest.raises(ValueError, match="unsupported selective action"):
        SelectiveDecision("bad", ("reason",), compatible)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at least one reason"):
        SelectiveDecision("review", (), compatible)
    with pytest.raises(ValueError, match="final evidence verdict"):
        SelectiveDecision("verify", ("reason",), compatible, "confirmed")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="unsupported contract value"):
        canonical_contract_json({1, 2})


def test_claim_parses_grouped_decimal_comma_and_percent_numbers() -> None:
    grouped = _claim(
        value=1234.5,
        source_text="Accuracy 1,234.5",
        metric_span=(0, 8),
        value_span=(9, 16),
    )
    decimal = _claim(
        value=1.25,
        source_text="Accuracy 1,25",
        metric_span=(0, 8),
        value_span=(9, 13),
    )
    percent = _claim(
        value=0.94,
        unit="percent",
        source_text="Accuracy 94",
        metric_span=(0, 8),
        value_span=(9, 11),
    )
    assert (grouped.value, decimal.value, percent.value) == (1234.5, 1.25, 0.94)

    grouped_integer = _claim(
        value=1234,
        source_text="Accuracy 1,234",
        metric_span=(0, 8),
        value_span=(9, 14),
    )
    assert grouped_integer.value == 1234


def test_claim_rejects_invalid_unit_and_whitespace_metric_binding() -> None:
    with pytest.raises(ValueError, match="unit"):
        _claim(unit="ratio")
    with pytest.raises(ValueError, match="non-empty source text"):
        _claim(
            source_text="X        0.94",
            metric_span=(1, 8),
            value_span=(9, 13),
            context={},
        )
