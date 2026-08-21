from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from .ml_contracts import canonical_contract_json
from .ml_extraction import enumerate_numeric_spans


PACKET_SCHEMA = "reprocheck.ml-annotation-packet.v1"
_METRIC = re.compile(
    r"\b(?:accuracy|precision|recall|specificity|f1(?:[- ]score)?|auroc|auc|auprc|"
    r"dice|iou|mAP|mean average precision|log[- ]loss|brier)\b",
    re.IGNORECASE,
)
_BREAK = re.compile(r"(?:\r?\n\s*){2,}")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).strip()).casefold()


def _blocks(text: str, minimum: int, maximum: int) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    starts = [0, *(match.end() for match in _BREAK.finditer(text))]
    ends = [*(match.start() for match in _BREAK.finditer(text)), len(text)]
    for start, end in zip(starts, ends, strict=True):
        raw = text[start:end].strip()
        if not raw:
            continue
        left = text[start:end].find(raw)
        start += left
        end = start + len(raw)
        if minimum <= len(raw) <= maximum:
            result.append((start, end, raw))
    return result


def build_annotation_packets(
    corpus: dict[str, Any],
    *,
    sources_root: Path,
    seed: int,
    minimum_characters: int = 20,
    maximum_characters: int = 1_500,
    negative_ratio: float = 1.0,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if minimum_characters < 1 or maximum_characters < minimum_characters:
        raise ValueError("annotation block character limits are invalid")
    if not 0 <= negative_ratio <= 5:
        raise ValueError("negative_ratio must be between zero and five")
    repositories = corpus.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("corpus contains no repositories")
    candidates: list[dict[str, Any]] = []
    negatives: list[dict[str, Any]] = []
    for repository in repositories:
        for artifact in repository["artifacts"]:
            relative = PurePosixPath(artifact["path"])
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise ValueError(f"unsafe artifact path: {artifact['artifact_id']}")
            path = sources_root.joinpath(*relative.parts)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
                raise ValueError(f"artifact checksum mismatch: {artifact['artifact_id']}")
            text = data.decode("utf-8")
            for start, end, raw in _blocks(text, minimum_characters, maximum_characters):
                numeric = enumerate_numeric_spans(raw)
                record = {
                    "repository_id": repository["repository_id"],
                    "artifact_id": artifact["artifact_id"],
                    "artifact_path": artifact["path"],
                    "source_start": start,
                    "source_end": end,
                    "raw_text": raw,
                    "normalized_text": _normalize(raw),
                    "metric_hint": bool(_METRIC.search(raw)),
                    "numeric_hint": bool(numeric),
                }
                (candidates if numeric and record["metric_hint"] else negatives).append(record)
    candidates.sort(key=lambda item: (item["repository_id"], item["artifact_id"], item["source_start"]))
    negatives.sort(key=lambda item: (item["repository_id"], item["artifact_id"], item["source_start"]))
    rng = random.Random(seed)
    negative_count = min(len(negatives), round(len(candidates) * negative_ratio))
    sampled_negatives = rng.sample(negatives, negative_count)
    selected = candidates + sampled_negatives
    mapping_blocks = []
    for item in selected:
        fingerprint = hashlib.sha256(
            f"{item['repository_id']}\0{item['artifact_id']}\0{item['source_start']}\0{item['source_end']}".encode()
        ).hexdigest()
        mapping_blocks.append({"blind_id": f"B-{fingerprint[:20]}", **item})
    mapping_blocks.sort(key=lambda item: item["blind_id"])
    mapping = {
        "schema_version": "reprocheck.ml-annotation-mapping.v1",
        "corpus_id": corpus["corpus_id"],
        "seed": seed,
        "candidate_count": len(candidates),
        "sampled_negative_count": negative_count,
        "blocks": mapping_blocks,
    }
    mapping_sha = hashlib.sha256(canonical_contract_json(mapping).encode()).hexdigest()

    def packet(reviewer: str, order_seed: int) -> dict[str, Any]:
        rows = [
            {
                "blind_id": item["blind_id"],
                "raw_text": item["raw_text"],
                "contains_eligible_claim": None,
                "claims": [],
                "reviewer_notes": "",
            }
            for item in mapping_blocks
        ]
        random.Random(order_seed).shuffle(rows)
        return {
            "schema_version": PACKET_SCHEMA,
            "corpus_id": corpus["corpus_id"],
            "reviewer": reviewer,
            "mapping_sha256": mapping_sha,
            "independent_review_required": True,
            "blocks": rows,
        }

    return packet("reviewer-a", seed ^ 0xA5A5), packet("reviewer-b", seed ^ 0x5A5A), mapping


def write_annotation_packets(
    corpus_path: Path, sources_root: Path, output_dir: Path, *, seed: int
) -> dict[str, int]:
    if output_dir.exists():
        raise ValueError("annotation packet output already exists")
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    first, second, mapping = build_annotation_packets(corpus, sources_root=sources_root, seed=seed)
    output_dir.mkdir(parents=True)
    for name, payload in (
        ("reviewer-a.json", first),
        ("reviewer-b.json", second),
        ("coordinator-mapping.json", mapping),
    ):
        (output_dir / name).write_text(canonical_contract_json(payload) + "\n", encoding="utf-8")
    return {
        "blocks": len(mapping["blocks"]),
        "candidates": mapping["candidate_count"],
        "sampled_negatives": mapping["sampled_negative_count"],
    }


def compare_annotation_reviews(
    first: dict[str, Any], second: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, Any]:
    if first.get("mapping_sha256") != second.get("mapping_sha256"):
        raise ValueError("review packets use different mappings")
    expected_mapping = hashlib.sha256(canonical_contract_json(mapping).encode()).hexdigest()
    if first.get("mapping_sha256") != expected_mapping:
        raise ValueError("review packet mapping digest is invalid")
    if first.get("reviewer") == second.get("reviewer"):
        raise ValueError("independent reviews require distinct reviewer identities")

    def indexed(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
        rows = packet.get("blocks")
        if not isinstance(rows, list):
            raise ValueError("review packet blocks must be an array")
        result = {str(row.get("blind_id")): row for row in rows if isinstance(row, dict)}
        if len(result) != len(rows):
            raise ValueError("review packet contains malformed or duplicate blocks")
        return result

    left, right = indexed(first), indexed(second)
    expected = {item["blind_id"] for item in mapping["blocks"]}
    if set(left) != expected or set(right) != expected:
        raise ValueError("review packets do not cover the complete mapping")
    agreements: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    for blind_id in sorted(expected):
        a, b = left[blind_id], right[blind_id]
        for row in (a, b):
            if not isinstance(row.get("contains_eligible_claim"), bool):
                raise ValueError(f"review is incomplete: {blind_id}")
            if not isinstance(row.get("claims"), list):
                raise ValueError(f"review claims must be an array: {blind_id}")
            if bool(row["claims"]) != row["contains_eligible_claim"]:
                raise ValueError(f"review decision disagrees with claims: {blind_id}")
        a_label = {"contains_eligible_claim": a["contains_eligible_claim"], "claims": a["claims"]}
        b_label = {"contains_eligible_claim": b["contains_eligible_claim"], "claims": b["claims"]}
        if canonical_contract_json(a_label) == canonical_contract_json(b_label):
            agreements.append({"blind_id": blind_id, **a_label, "review_status": "agreed"})
        else:
            disagreements.append(
                {
                    "blind_id": blind_id,
                    "reviewer_a": a_label,
                    "reviewer_b": b_label,
                    "adjudicated_label": None,
                    "adjudicator_notes": "",
                }
            )
    total = len(expected)
    return {
        "schema_version": "reprocheck.ml-review-comparison.v1",
        "mapping_sha256": expected_mapping,
        "reviewer_a": first["reviewer"],
        "reviewer_b": second["reviewer"],
        "block_count": total,
        "agreement_count": len(agreements),
        "disagreement_count": len(disagreements),
        "exact_agreement": len(agreements) / total if total else 0.0,
        "agreements": agreements,
        "adjudication_queue": disagreements,
    }
