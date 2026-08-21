from __future__ import annotations

from reprocheck.ml_split import build_owner_disjoint_split, cross_split_leakage


def _records() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    repositories: list[dict[str, str]] = []
    blocks: list[dict[str, str]] = []
    domains = ("vision", "nlp", "other")
    for domain in domains:
        for index in range(5):
            repository_id = f"{domain}-{index}"
            repositories.append(
                {
                    "repository_id": repository_id,
                    "owner_id": f"owner-{repository_id}",
                    "domain": domain,
                    "lineage_id": f"repository-lineage-{repository_id}",
                }
            )
            blocks.append(
                {
                    "block_id": f"block-{repository_id}",
                    "repository_id": repository_id,
                    "lineage_id": f"block-lineage-{repository_id}",
                    "raw_text": f"{domain} result {index} reached {80 + index}% accuracy",
                }
            )
    return repositories, blocks


def test_split_is_deterministic_owner_disjoint_and_domain_aware() -> None:
    repositories, blocks = _records()
    first = build_owner_disjoint_split(repositories, blocks, seed=20260821)
    second = build_owner_disjoint_split(repositories, blocks, seed=20260821)
    assert first == second
    assert first["split_sha256"] == second["split_sha256"]
    assert first["counts"] == {"train": 9, "validation": 3, "test": 3}
    assert first["domain_counts"]["test"] == {"nlp": 1, "other": 1, "vision": 1}
    assigned = [repo for split in first["splits"].values() for repo in split]
    assert sorted(assigned) == sorted(repo["repository_id"] for repo in repositories)


def test_shared_lineage_is_atomic() -> None:
    repositories, blocks = _records()
    repositories[0]["lineage_id"] = "shared-lineage"
    repositories[1]["lineage_id"] = "shared-lineage"
    result = build_owner_disjoint_split(repositories, blocks, seed=7)
    locations = {
        repository_id: split
        for split, repository_ids in result["splits"].items()
        for repository_id in repository_ids
    }
    assert locations[repositories[0]["repository_id"]] == locations[repositories[1]["repository_id"]]


def test_split_rejects_prospective_owner_overlap_and_infeasible_domains() -> None:
    repositories, blocks = _records()
    try:
        build_owner_disjoint_split(
            repositories,
            blocks,
            seed=1,
            prospective_owner_ids={repositories[0]["owner_id"]},
        )
    except ValueError as error:
        assert "prospective owner" in str(error)
    else:
        raise AssertionError("prospective owner overlap must fail")

    reduced = [repo for repo in repositories if repo["domain"] != "nlp" or repo["repository_id"].endswith(("0", "1"))]
    reduced_ids = {repo["repository_id"] for repo in reduced}
    try:
        build_owner_disjoint_split(
            reduced,
            [block for block in blocks if block["repository_id"] in reduced_ids],
            seed=1,
        )
    except ValueError as error:
        assert "domain-aware split infeasible" in str(error)
    else:
        raise AssertionError("a domain with fewer than three atomic groups must fail")


def test_cross_split_leakage_reports_exact_and_near_duplicates() -> None:
    repositories, blocks = _records()
    split = build_owner_disjoint_split(repositories, blocks, seed=20260821)
    locations = {
        repository_id: name
        for name, repository_ids in split["splits"].items()
        for repository_id in repository_ids
    }
    train_repo = next(repo for repo, name in locations.items() if name == "train")
    test_repo = next(repo for repo, name in locations.items() if name == "test")
    train_block = next(block for block in blocks if block["repository_id"] == train_repo)
    test_block = next(block for block in blocks if block["repository_id"] == test_repo)
    test_block["raw_text"] = train_block["raw_text"].upper()
    exact = cross_split_leakage(blocks, split)
    assert exact["exact_pair_count"] >= 1

    test_block["raw_text"] = train_block["raw_text"] + "!"
    near = cross_split_leakage(blocks, split, near_threshold=0.90)
    assert near["near_pair_count"] >= 1
    assert near["status"] == "leakage_detected"

