from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import defaultdict
from typing import Any, Iterable

from .leakage import find_text_matches


SPLIT_NAMES = ("train", "validation", "test")


class _UnionFind:
    def __init__(self, values: Iterable[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _allocation(group_count: int, ratios: tuple[float, float, float]) -> dict[str, int]:
    if group_count < 3:
        raise ValueError("domain-aware split infeasible: each domain needs three atomic groups")
    counts = {name: 1 for name in SPLIT_NAMES}
    targets = {name: group_count * ratio for name, ratio in zip(SPLIT_NAMES, ratios)}
    for _ in range(group_count - 3):
        selected = max(
            SPLIT_NAMES, key=lambda name: (targets[name] - counts[name], -SPLIT_NAMES.index(name))
        )
        counts[selected] += 1
    return counts


def build_owner_disjoint_split(
    repositories: list[dict[str, str]],
    blocks: list[dict[str, str]],
    *,
    seed: int,
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    prospective_owner_ids: set[str] | None = None,
) -> dict[str, Any]:
    if len(ratios) != 3 or any(value <= 0 for value in ratios) or abs(sum(ratios) - 1) > 1e-9:
        raise ValueError("split ratios must contain three positive values summing to one")
    repository_ids = [item["repository_id"] for item in repositories]
    owner_ids = [item["owner_id"] for item in repositories]
    if len(set(repository_ids)) != len(repository_ids):
        raise ValueError("repository_id values must be unique")
    if len(set(owner_ids)) != len(owner_ids):
        raise ValueError("owner groups must be unique before splitting")
    overlap = sorted(set(owner_ids) & (prospective_owner_ids or set()))
    if overlap:
        raise ValueError(f"prospective owner appears in development corpus: {overlap[0]}")

    repository_by_id = {item["repository_id"]: item for item in repositories}
    union = _UnionFind(repository_ids)
    lineage_members: dict[str, list[str]] = defaultdict(list)
    for repository in repositories:
        lineage_members[f"repository:{repository['lineage_id']}"].append(
            repository["repository_id"]
        )
    for block in blocks:
        repository_id = block["repository_id"]
        if repository_id not in repository_by_id:
            raise ValueError(f"block references unknown repository: {repository_id}")
        lineage_members[f"block:{block['lineage_id']}"].append(repository_id)
    for members in lineage_members.values():
        for member in members[1:]:
            union.union(members[0], member)

    grouped: dict[str, list[str]] = defaultdict(list)
    for repository_id in repository_ids:
        grouped[union.find(repository_id)].append(repository_id)
    by_domain: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    for members in grouped.values():
        domains = {repository_by_id[item]["domain"] for item in members}
        if len(domains) != 1:
            raise ValueError("an atomic lineage group cannot span multiple domains")
        by_domain[next(iter(domains))].append(tuple(sorted(members)))

    splits: dict[str, list[str]] = {name: [] for name in SPLIT_NAMES}
    for domain in sorted(by_domain):
        groups = sorted(by_domain[domain])
        rng = random.Random(f"{seed}:{domain}")
        rng.shuffle(groups)
        counts = _allocation(len(groups), ratios)
        cursor = 0
        for name in SPLIT_NAMES:
            selected = groups[cursor : cursor + counts[name]]
            cursor += counts[name]
            splits[name].extend(repository_id for group in selected for repository_id in group)

    for values in splits.values():
        values.sort()
    domain_counts = {
        name: dict(
            sorted(
                {
                    domain: sum(repository_by_id[item]["domain"] == domain for item in values)
                    for domain in by_domain
                }.items()
            )
        )
        for name, values in splits.items()
    }
    payload: dict[str, Any] = {
        "schema_version": "reprocheck.ml-split.v1",
        "seed": seed,
        "ratios": dict(zip(SPLIT_NAMES, ratios)),
        "splits": splits,
        "counts": {name: len(values) for name, values in splits.items()},
        "domain_counts": domain_counts,
        "prospective_owner_exclusions": sorted(prospective_owner_ids or set()),
        "split_sha256": "",
    }
    payload["split_sha256"] = _canonical_digest({**payload, "split_sha256": ""})
    return payload


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip()).casefold()


def cross_split_leakage(
    blocks: list[dict[str, str]], split: dict[str, Any], *, near_threshold: float = 0.90
) -> dict[str, Any]:
    if not 0 <= near_threshold <= 1:
        raise ValueError("near threshold must be between 0 and 1")
    locations = {
        repository_id: name
        for name, repository_ids in split["splits"].items()
        for repository_id in repository_ids
    }
    texts: dict[str, list[tuple[str, str]]] = {name: [] for name in SPLIT_NAMES}
    exact_locations: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for block in blocks:
        repository_id = block["repository_id"]
        if repository_id not in locations:
            raise ValueError(f"block repository is absent from split: {repository_id}")
        name = locations[repository_id]
        normalized = _normalize(block["raw_text"])
        texts[name].append((block["block_id"], normalized))
        exact_locations[normalized].append((name, block["block_id"]))

    exact_pairs: list[dict[str, str]] = []
    for members in exact_locations.values():
        for left_index, left in enumerate(members):
            for right in members[left_index + 1 :]:
                if left[0] != right[0]:
                    exact_pairs.append(
                        {
                            "left_split": left[0],
                            "left_block": left[1],
                            "right_split": right[0],
                            "right_block": right[1],
                        }
                    )

    near_pairs: list[dict[str, Any]] = []
    for left_name, right_name in (
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ):
        left = texts[left_name]
        right = texts[right_name]
        search = find_text_matches(
            [item[1] for item in left],
            [item[1] for item in right],
            threshold=near_threshold,
            method="hybrid_lexical_v1",
        )
        for match in search.matches:
            if right[match.test_index][1] == left[match.train_index][1]:
                continue
            near_pairs.append(
                {
                    "left_split": left_name,
                    "left_block": left[match.train_index][0],
                    "right_split": right_name,
                    "right_block": right[match.test_index][0],
                    "similarity": match.similarity,
                }
            )
    exact_pairs.sort(key=lambda item: tuple(str(value) for value in item.values()))
    near_pairs.sort(key=lambda item: tuple(str(value) for value in item.values()))
    return {
        "schema_version": "reprocheck.ml-leakage.v1",
        "status": "leakage_detected" if exact_pairs or near_pairs else "clear",
        "exact_pair_count": len(exact_pairs),
        "near_pair_count": len(near_pairs),
        "exact_pairs": exact_pairs,
        "near_pairs": near_pairs,
        "near_threshold": near_threshold,
        "method": "hybrid_lexical_v1",
    }
