from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def prepare_external_review(
    corpus_root: Path,
    output_dir: Path,
    *,
    sample_artifacts: int = 16,
) -> dict[str, Any]:
    """Create a label-hidden packet and a separate internal answer key."""
    if sample_artifacts < 2 or sample_artifacts % 2:
        raise ValueError("external review sample size must be an even integer of at least 2")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("external review output directory must be empty")
    corpus_root = corpus_root.resolve()
    annotations_path = corpus_root / "annotations.json"
    annotations = _load_object(annotations_path)
    raw_artifacts = annotations.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise ValueError("external review annotations must contain an artifacts array")
    positives = [item for item in raw_artifacts if _expected_claims(item)]
    negatives = [item for item in raw_artifacts if not _expected_claims(item)]
    per_stratum = sample_artifacts // 2
    if len(positives) < per_stratum or len(negatives) < per_stratum:
        raise ValueError("external review corpus is too small for the requested balanced sample")
    selected = [
        *_hash_ranked(positives, per_stratum),
        *_hash_ranked(negatives, per_stratum),
    ]
    selected.sort(key=lambda item: _blind_id(str(item["local_path"])))

    output_dir.mkdir(parents=True, exist_ok=True)
    public_dir = output_dir / "public"
    private_dir = output_dir / "private"
    public_dir.mkdir()
    private_dir.mkdir()
    source_dir = public_dir / "packet-sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    packet_items: list[dict[str, Any]] = []
    gold_items: list[dict[str, Any]] = []
    response_items: list[dict[str, Any]] = []
    for item in selected:
        local_path = _local_path(item)
        source = (corpus_root / "sources" / local_path).resolve()
        if not source.is_relative_to((corpus_root / "sources").resolve()) or not source.is_file():
            raise ValueError(f"unsafe or missing external review source: {local_path}")
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        expected_digest = item.get("source_sha256")
        if digest != expected_digest:
            raise ValueError(f"external review source checksum mismatch: {local_path}")
        blind_id = _blind_id(local_path)
        suffix = source.suffix if source.suffix else ".txt"
        packet_source = source_dir / f"{blind_id}{suffix}"
        packet_source.write_bytes(payload)
        packet_items.append(
            {
                "blind_id": blind_id,
                "repository": item.get("repository"),
                "source_file": f"packet-sources/{packet_source.name}",
                "source_sha256": digest,
                "instructions": "List every in-scope numerical metric claim, or leave claims empty.",
            }
        )
        gold_items.append(
            {
                "blind_id": blind_id,
                "local_path": local_path,
                "expected_claims": [
                    {"metric": claim["metric"], "value": float(claim["value"])}
                    for claim in _expected_claims(item)
                ],
            }
        )
        response_items.append({"blind_id": blind_id, "claims": [], "notes": ""})

    packet = {
        "schema": "reprocheck.external-review-packet.v1",
        "blind": True,
        "selection": {
            "method": "sha256-ranked balanced artifact sample",
            "sample_artifacts": sample_artifacts,
            "claim_bearing_artifacts": per_stratum,
            "zero-claim_artifacts": per_stratum,
        },
        "annotation_scope": (
            "Extract numerical model-evaluation claims from the supplied complete files. "
            "Do not inspect source annotations, evaluator output, or the private gold file."
        ),
        "items": packet_items,
    }
    gold = {
        "schema": "reprocheck.external-review-gold.v1",
        "annotations_sha256": _sha256_file(annotations_path),
        "items": gold_items,
        "scientific_boundary": (
            "This key contains the project's internal labels. External reviewers must not "
            "receive it before both independent responses are frozen."
        ),
    }
    _claim_map(gold_items, "expected_claims")
    template = {
        "schema": "reprocheck.external-review-response.v1",
        "reviewer_id": "REPLACE_WITH_REVIEWER_ID",
        "independent_review_confirmed": False,
        "items": response_items,
    }
    packet_path = public_dir / "packet.json"
    gold_path = private_dir / "PRIVATE-gold.json"
    reviewer_a_path = public_dir / "reviewer-A.json"
    reviewer_b_path = public_dir / "reviewer-B.json"
    _write_json(packet_path, packet)
    _write_json(gold_path, gold)
    _write_json(reviewer_a_path, template)
    _write_json(reviewer_b_path, template)
    manifest = {
        "schema": "reprocheck.external-review-manifest.v1",
        "distribute_only": "public/",
        "keep_private_until_responses_frozen": "private/PRIVATE-gold.json",
        "files": {
            path.relative_to(output_dir).as_posix(): _sha256_file(path)
            for path in (packet_path, gold_path, reviewer_a_path, reviewer_b_path)
        },
        "external_reviews_completed": 0,
        "adjudication_completed": False,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def score_external_review(
    gold_path: Path,
    reviewer_paths: list[Path],
    output: Path | None = None,
    *,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    if len(reviewer_paths) != 2:
        raise ValueError("external review scoring requires exactly two reviewer files")
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValueError("external review tolerance must be finite and positive")
    if output is not None and output.exists():
        raise ValueError("external review result already exists")
    gold = _load_object(gold_path)
    if gold.get("schema") != "reprocheck.external-review-gold.v1":
        raise ValueError("unsupported external review gold schema")
    gold_items = _claim_map(gold.get("items"), "expected_claims")
    reviewers = [_load_reviewer(path, set(gold_items)) for path in reviewer_paths]
    reviewer_ids = [reviewer["reviewer_id"] for reviewer in reviewers]
    if len(set(reviewer_ids)) != 2:
        raise ValueError("external reviewers must have distinct reviewer_id values")

    summaries = {
        reviewer["reviewer_id"]: _score_claim_maps(
            gold_items, reviewer["claims"], tolerance=tolerance
        )
        for reviewer in reviewers
    }
    first, second = reviewers
    first_presence = [bool(first["claims"][item_id]) for item_id in sorted(gold_items)]
    second_presence = [bool(second["claims"][item_id]) for item_id in sorted(gold_items)]
    inter_reviewer_disagreements = [
        item_id
        for item_id in sorted(gold_items)
        if _claim_counter(first["claims"][item_id], tolerance)
        != _claim_counter(second["claims"][item_id], tolerance)
    ]
    internal_gold_disagreements = [
        item_id
        for item_id in sorted(gold_items)
        if _claim_counter(gold_items[item_id], tolerance)
        != _claim_counter(first["claims"][item_id], tolerance)
        or _claim_counter(gold_items[item_id], tolerance)
        != _claim_counter(second["claims"][item_id], tolerance)
    ]
    adjudication_ids = sorted(set(inter_reviewer_disagreements) | set(internal_gold_disagreements))
    inter_reviewer = _score_claim_maps(first["claims"], second["claims"], tolerance=tolerance)
    inter_reviewer.update(
        {
            "artifact_claim_presence_agreement": sum(
                left == right for left, right in zip(first_presence, second_presence)
            )
            / len(gold_items),
            "artifact_claim_presence_cohen_kappa": _cohen_kappa(first_presence, second_presence),
            "exact_artifact_agreement": 1 - len(inter_reviewer_disagreements) / len(gold_items),
            "inter_reviewer_disagreement_ids": inter_reviewer_disagreements,
            "internal_gold_disagreement_ids": internal_gold_disagreements,
            "adjudication_required_ids": adjudication_ids,
        }
    )
    result = {
        "schema": "reprocheck.external-review-result.v1",
        "reviewers": reviewer_ids,
        "reviewer_count": 2,
        "independent_reviews_confirmed": True,
        "input_sha256": {
            "gold": _sha256_file(gold_path),
            **{
                reviewer["reviewer_id"]: _sha256_file(path)
                for reviewer, path in zip(reviewers, reviewer_paths)
            },
        },
        "reviewer_vs_internal_gold": summaries,
        "inter_reviewer": inter_reviewer,
        "adjudication_required": bool(adjudication_ids),
        "external_validation_complete": not adjudication_ids,
        "scientific_boundary": (
            "Agreement with project labels validates annotation reliability on this sample; "
            "it does not create a new zero-shot evaluator result or prove scientific truth."
        ),
    }
    if output:
        _write_json(output, result)
    return result


def _load_reviewer(path: Path, expected_ids: set[str]) -> dict[str, Any]:
    payload = _load_object(path)
    if payload.get("schema") != "reprocheck.external-review-response.v1":
        raise ValueError(f"unsupported external review response schema: {path.name}")
    reviewer_id = payload.get("reviewer_id")
    if (
        not isinstance(reviewer_id, str)
        or not reviewer_id.strip()
        or reviewer_id.startswith("REPLACE")
    ):
        raise ValueError(f"external review response has no reviewer_id: {path.name}")
    if payload.get("independent_review_confirmed") is not True:
        raise ValueError(f"external reviewer did not confirm independence: {path.name}")
    claims = _claim_map(payload.get("items"), "claims")
    if set(claims) != expected_ids:
        raise ValueError(f"external review response item ids do not match gold: {path.name}")
    return {"reviewer_id": reviewer_id, "claims": claims}


def _claim_map(items: object, claim_key: str) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(items, list) or not items:
        raise ValueError("external review items must be a non-empty array")
    result: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("external review item must be an object")
        blind_id = item.get("blind_id")
        claims = item.get(claim_key)
        if not isinstance(blind_id, str) or not blind_id or blind_id in result:
            raise ValueError("external review item ids must be non-empty and unique")
        if not isinstance(claims, list):
            raise ValueError(f"external review {claim_key} must be an array")
        normalized = []
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("metric"), str):
                raise ValueError("external review claim must contain a metric")
            value = claim.get("value")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("external review claim value must be finite and numeric")
            normalized.append({"metric": claim["metric"], "value": float(value)})
        result[blind_id] = normalized
    return result


def _score_claim_maps(
    reference: dict[str, list[dict[str, Any]]],
    candidate: dict[str, list[dict[str, Any]]],
    *,
    tolerance: float,
) -> dict[str, Any]:
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    exact_artifacts = 0
    for item_id, expected in reference.items():
        actual = candidate[item_id]
        remaining = list(expected)
        matched = 0
        for claim in actual:
            match = next(
                (
                    index
                    for index, target in enumerate(remaining)
                    if claim["metric"] == target["metric"]
                    and abs(claim["value"] - target["value"]) <= tolerance
                ),
                None,
            )
            if match is not None:
                matched += 1
                remaining.pop(match)
        true_positives += matched
        false_positives += len(actual) - matched
        false_negatives += len(remaining)
        exact_artifacts += int(matched == len(actual) == len(expected))
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 1.0
    )
    return {
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "exact_artifact_rate": exact_artifacts / len(reference),
    }


def _cohen_kappa(first: list[bool], second: list[bool]) -> float | None:
    if len(first) != len(second) or not first:
        raise ValueError("Cohen kappa requires equal non-empty label vectors")
    observed = sum(left == right for left, right in zip(first, second)) / len(first)
    first_positive = sum(first) / len(first)
    second_positive = sum(second) / len(second)
    expected = first_positive * second_positive + (1 - first_positive) * (1 - second_positive)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def _claim_counter(claims: list[dict[str, Any]], tolerance: float) -> Counter[tuple[str, int]]:
    scale = max(1, round(1 / tolerance))
    return Counter((claim["metric"], round(claim["value"] * scale)) for claim in claims)


def _hash_ranked(items: list[dict[str, Any]], amount: int) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: hashlib.sha256(_local_path(item).encode()).hexdigest())[
        :amount
    ]


def _blind_id(local_path: str) -> str:
    return "R-" + hashlib.sha256(("reprocheck-review-v1:" + local_path).encode()).hexdigest()[:12]


def _local_path(item: object) -> str:
    if not isinstance(item, dict) or not isinstance(item.get("local_path"), str):
        raise ValueError("external review artifact must declare local_path")
    return item["local_path"]


def _expected_claims(item: object) -> list[dict[str, Any]]:
    if not isinstance(item, dict) or not isinstance(item.get("expected_claims"), list):
        raise ValueError("external review artifact must declare expected_claims")
    return item["expected_claims"]


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read external review file {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"external review file must be an object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
