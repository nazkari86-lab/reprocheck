from __future__ import annotations

import re
import unicodedata

from .metric_names import canonical_metric
from .ml_contracts import (
    CompatibilityResult,
    EvidenceCandidate,
    MLClaimTuple,
    ModelScores,
    SelectiveDecision,
    SelectiveThresholds,
)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip()).casefold()


def check_evidence_compatibility(
    claim: MLClaimTuple, candidate: EvidenceCandidate
) -> CompatibilityResult:
    matched: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []

    if candidate.metric is None:
        missing.append("metric")
    elif canonical_metric(candidate.metric) == canonical_metric(claim.metric):
        matched.append("metric")
    else:
        conflicts.append("metric")

    for field_name, claim_value in sorted(claim.context.items()):
        evidence_value = candidate.context.get(field_name)
        if evidence_value is None:
            missing.append(field_name)
        elif _normalized(evidence_value) == _normalized(claim_value):
            matched.append(field_name)
        else:
            conflicts.append(field_name)

    required_count = 1 + len(claim.context)
    completeness = len(matched) / required_count
    return CompatibilityResult(
        compatible=not conflicts,
        completeness=completeness,
        matched=tuple(sorted(matched)),
        missing=tuple(sorted(missing)),
        conflicts=tuple(sorted(conflicts)),
    )


def select_ml_action(
    claim: MLClaimTuple,
    candidate: EvidenceCandidate,
    scores: ModelScores,
    thresholds: SelectiveThresholds,
) -> SelectiveDecision:
    compatibility = check_evidence_compatibility(claim, candidate)
    if not candidate.integrity_verified:
        return _decision("abstain", ("artifact_integrity_not_verified",), compatibility)
    if compatibility.conflicts:
        reasons = tuple(f"context_conflict:{field}" for field in compatibility.conflicts)
        return _decision("abstain", reasons, compatibility)

    below_review: list[str] = []
    if scores.claim_probability < thresholds.review_claim_probability:
        below_review.append("claim_probability_below_review_threshold")
    if scores.tuple_probability < thresholds.review_tuple_probability:
        below_review.append("tuple_probability_below_review_threshold")
    if scores.evidence_probability < thresholds.review_evidence_probability:
        below_review.append("evidence_probability_below_review_threshold")
    if below_review:
        return _decision("abstain", tuple(below_review), compatibility)

    review_reasons: list[str] = []
    if candidate.evidence_grade == "text_reported":
        review_reasons.append("text_only_evidence")
    if scores.out_of_distribution_score > thresholds.maximum_ood_score:
        review_reasons.append("out_of_distribution")
    if compatibility.completeness < thresholds.minimum_completeness:
        fields = ",".join(compatibility.missing)
        review_reasons.append(f"incomplete_evidence:{fields}")
    if candidate.rank_margin < thresholds.minimum_rank_margin:
        review_reasons.append("ambiguous_evidence_ranking")

    automatic_scores_pass = (
        scores.claim_probability >= thresholds.verify_claim_probability
        and scores.tuple_probability >= thresholds.verify_tuple_probability
        and scores.evidence_probability >= thresholds.verify_evidence_probability
    )
    if not automatic_scores_pass:
        review_reasons.append("below_automatic_threshold")
    if review_reasons:
        return _decision("review", tuple(review_reasons), compatibility)
    return _decision(
        "verify", ("eligible_for_deterministic_verification",), compatibility
    )


def _decision(
    action: str, reasons: tuple[str, ...], compatibility: CompatibilityResult
) -> SelectiveDecision:
    if action == "verify":
        resolved = "verify"
    elif action == "review":
        resolved = "review"
    else:
        resolved = "abstain"
    return SelectiveDecision(action=resolved, reasons=reasons, compatibility=compatibility)

