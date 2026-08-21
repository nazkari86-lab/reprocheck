from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace
from typing import Any, Mapping

from .metric_names import canonical_metric
from .ml_contracts import (
    EvidenceCandidate,
    MLClaimTuple,
    canonical_contract_json,
)
from .ml_decision import check_evidence_compatibility


SUPPORTED_ROLES = frozenset({"report", "metrics", "predictions", "detection"})
FEATURE_NAMES = (
    "metric_match",
    "metric_missing",
    "context_match_ratio",
    "context_missing_ratio",
    "context_conflict_ratio",
    "raw_recomputed",
    "structured_reported",
    "text_reported",
    "role_predictions",
    "role_metrics",
    "role_detection",
    "role_report",
    "integrity_verified",
)


@dataclass(frozen=True)
class RetrievalCandidate:
    artifact_id: str
    role: str
    metric_names: tuple[str, ...]
    context: Mapping[str, str]
    evidence_grade: str
    integrity_verified: bool
    compatible: bool
    completeness: float
    conflicts: tuple[str, ...]


@dataclass(frozen=True)
class RankedEvidence:
    artifact_id: str
    score: float
    compatible: bool
    completeness: float
    conflicts: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceRankerModel:
    schema_version: str
    corpus_sha256: str
    split_sha256: str
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float
    training_pair_count: int
    hard_negative_count: int
    epochs: int
    learning_rate: float
    l2: float
    training_data_sha256: str
    model_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "corpus_sha256": self.corpus_sha256,
            "split_sha256": self.split_sha256,
            "feature_names": list(self.feature_names),
            "coefficients": list(self.coefficients),
            "intercept": self.intercept,
            "training_pair_count": self.training_pair_count,
            "hard_negative_count": self.hard_negative_count,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "training_data_sha256": self.training_data_sha256,
            "model_sha256": self.model_sha256,
        }


def _artifact_candidate(claim: MLClaimTuple, artifact: dict[str, object]) -> RetrievalCandidate:
    required = {
        "artifact_id",
        "role",
        "metric_names",
        "context",
        "evidence_grade",
        "integrity_verified",
    }
    if set(artifact) != required:
        raise ValueError("retrieval artifacts must contain the exact declared fields")
    role = str(artifact["role"])
    metric_names = tuple(canonical_metric(str(item)) for item in artifact["metric_names"])  # type: ignore[union-attr]
    selected_metric = claim.metric if canonical_metric(claim.metric) in metric_names else None
    candidate = EvidenceCandidate(
        candidate_id=f"{claim.claim_id}:{artifact['artifact_id']}",
        artifact_id=str(artifact["artifact_id"]),
        evidence_grade=str(artifact["evidence_grade"]),  # type: ignore[arg-type]
        metric=selected_metric,
        value=None,
        context=dict(artifact["context"]),  # type: ignore[arg-type]
        rank_score=0.0,
        rank_margin=0.0,
        integrity_verified=artifact["integrity_verified"],  # type: ignore[arg-type]
    )
    compatibility = check_evidence_compatibility(claim, candidate)
    return RetrievalCandidate(
        artifact_id=candidate.artifact_id,
        role=role,
        metric_names=metric_names,
        context=candidate.context,
        evidence_grade=candidate.evidence_grade,
        integrity_verified=candidate.integrity_verified,
        compatible=compatibility.compatible,
        completeness=compatibility.completeness,
        conflicts=compatibility.conflicts,
    )


def generate_evidence_candidates(
    claim: MLClaimTuple, artifacts: list[dict[str, object]]
) -> tuple[RetrievalCandidate, ...]:
    candidates = [
        _artifact_candidate(claim, artifact)
        for artifact in artifacts
        if str(artifact.get("role")) in SUPPORTED_ROLES
    ]
    identifiers = [item.artifact_id for item in candidates]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("retrieval artifact_id values must be unique")
    return tuple(sorted(candidates, key=lambda item: item.artifact_id))


def _features(claim: MLClaimTuple, candidate: RetrievalCandidate) -> tuple[float, ...]:
    claim_metric = canonical_metric(claim.metric)
    metric_match = float(claim_metric in candidate.metric_names)
    context_total = max(1, len(claim.context))
    matched = missing = conflicts = 0
    for field_name, claim_value in claim.context.items():
        evidence_value = candidate.context.get(field_name)
        if evidence_value is None:
            missing += 1
        elif evidence_value.strip().casefold() == claim_value.strip().casefold():
            matched += 1
        else:
            conflicts += 1
    values = {
        "metric_match": metric_match,
        "metric_missing": float(not candidate.metric_names),
        "context_match_ratio": matched / context_total,
        "context_missing_ratio": missing / context_total,
        "context_conflict_ratio": conflicts / context_total,
        "raw_recomputed": float(candidate.evidence_grade == "raw_recomputed"),
        "structured_reported": float(candidate.evidence_grade == "structured_reported"),
        "text_reported": float(candidate.evidence_grade == "text_reported"),
        "role_predictions": float(candidate.role == "predictions"),
        "role_metrics": float(candidate.role == "metrics"),
        "role_detection": float(candidate.role == "detection"),
        "role_report": float(candidate.role == "report"),
        "integrity_verified": float(candidate.integrity_verified),
    }
    return tuple(values[name] for name in FEATURE_NAMES)


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1 / (1 + inverse)
    exponent = math.exp(value)
    return exponent / (1 + exponent)


def train_evidence_ranker(
    pairs: list[dict[str, object]],
    *,
    corpus_sha256: str,
    split_sha256: str,
    epochs: int = 300,
    learning_rate: float = 0.5,
    l2: float = 0.001,
) -> EvidenceRankerModel:
    if len(corpus_sha256) != 64 or len(split_sha256) != 64:
        raise ValueError("ranker corpus and split digests must be SHA-256 values")
    if not pairs or epochs < 1 or learning_rate <= 0 or l2 < 0:
        raise ValueError("ranker training parameters must be positive")
    vectors: list[tuple[float, ...]] = []
    labels: list[bool] = []
    normalized: list[dict[str, object]] = []
    hard_negative_count = 0
    for pair in pairs:
        if set(pair) != {"claim", "artifact", "label", "hard_negative", "split"}:
            raise ValueError("ranker pairs must contain the exact declared fields")
        if pair["split"] != "train":
            raise ValueError("ranker pairs must belong to the training split")
        if not isinstance(pair["claim"], MLClaimTuple):
            raise ValueError("ranker claim must be an MLClaimTuple")
        if not isinstance(pair["artifact"], dict):
            raise ValueError("ranker artifact must be an object")
        if not isinstance(pair["label"], bool) or not isinstance(pair["hard_negative"], bool):
            raise ValueError("ranker labels must be boolean")
        candidate = _artifact_candidate(pair["claim"], pair["artifact"])
        vectors.append(_features(pair["claim"], candidate))
        labels.append(pair["label"])
        hard_negative_count += int(pair["hard_negative"] and not pair["label"])
        normalized.append(
            {
                "claim_id": pair["claim"].claim_id,
                "artifact_id": candidate.artifact_id,
                "label": pair["label"],
                "hard_negative": pair["hard_negative"],
                "features": list(vectors[-1]),
            }
        )
    if len(set(labels)) != 2:
        raise ValueError("ranker training requires positive and negative pairs")
    weights = [0.0] * len(FEATURE_NAMES)
    intercept = 0.0
    for _ in range(epochs):
        gradient = [0.0] * len(weights)
        intercept_gradient = 0.0
        for vector, label in zip(vectors, labels):
            error = _sigmoid(intercept + sum(w * x for w, x in zip(weights, vector))) - float(label)
            intercept_gradient += error
            for index, value in enumerate(vector):
                gradient[index] += error * value
        scale = 1 / len(vectors)
        for index in range(len(weights)):
            weights[index] -= learning_rate * (gradient[index] * scale + l2 * weights[index])
        intercept -= learning_rate * intercept_gradient * scale
    training_digest = hashlib.sha256(
        canonical_contract_json(
            sorted(normalized, key=lambda item: (str(item["claim_id"]), str(item["artifact_id"])))
        ).encode("utf-8")
    ).hexdigest()
    model = EvidenceRankerModel(
        schema_version="reprocheck.evidence-ranker.v1",
        corpus_sha256=corpus_sha256,
        split_sha256=split_sha256,
        feature_names=FEATURE_NAMES,
        coefficients=tuple(weights),
        intercept=intercept,
        training_pair_count=len(pairs),
        hard_negative_count=hard_negative_count,
        epochs=epochs,
        learning_rate=learning_rate,
        l2=l2,
        training_data_sha256=training_digest,
        model_sha256="",
    )
    digest = hashlib.sha256(canonical_contract_json(model.to_dict()).encode("utf-8")).hexdigest()
    return replace(model, model_sha256=digest)


def rank_evidence_candidates(
    model: EvidenceRankerModel,
    claim: MLClaimTuple,
    candidates: tuple[RetrievalCandidate, ...],
) -> tuple[RankedEvidence, ...]:
    if model.feature_names != FEATURE_NAMES or len(model.coefficients) != len(FEATURE_NAMES):
        raise ValueError("ranker model feature contract does not match")
    ranked = []
    for candidate in candidates:
        vector = _features(claim, candidate)
        score = _sigmoid(model.intercept + sum(w * x for w, x in zip(model.coefficients, vector)))
        ranked.append(
            RankedEvidence(
                artifact_id=candidate.artifact_id,
                score=score,
                compatible=candidate.compatible,
                completeness=candidate.completeness,
                conflicts=candidate.conflicts,
            )
        )
    return tuple(sorted(ranked, key=lambda item: (-item.score, item.artifact_id)))


def score_evidence_ranking(cases: list[dict[str, object]]) -> dict[str, float | int]:
    claim_ids = [str(case["claim_id"]) for case in cases]
    if len(set(claim_ids)) != len(claim_ids):
        raise ValueError("ranking cases require unique claim_id values")
    reciprocal_sum = 0.0
    at_one = at_three = 0
    for case in cases:
        expected = str(case["expected_artifact_id"])
        ranked = [str(item) for item in case["ranked_artifact_ids"]]  # type: ignore[union-attr]
        if expected in ranked:
            rank = ranked.index(expected) + 1
            reciprocal_sum += 1 / rank
            at_one += int(rank <= 1)
            at_three += int(rank <= 3)
    count = len(cases)
    return {
        "claims": count,
        "recall_at_1": at_one / count if count else 0.0,
        "recall_at_3": at_three / count if count else 0.0,
        "mrr": reciprocal_sum / count if count else 0.0,
    }
