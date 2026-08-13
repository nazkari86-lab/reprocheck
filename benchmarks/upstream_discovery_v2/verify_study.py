from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPECTED_EVALUATOR = "2618cad2c54c1610947f4f64e4b7ba8c5302fa28"
EXPECTED_QUERIES = [
    '"incorrect benchmark" in:title,body is:merged',
    '"wrong benchmark" in:title,body is:merged',
    '"correct benchmark" in:title,body is:merged',
]
SEED = "reprocheck-upstream-v2"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sample_digest(repository: str, pull_request: int) -> str:
    payload = f"{SEED}|{repository}#{pull_request}".encode()
    return hashlib.sha256(payload).hexdigest()


def verify() -> dict[str, object]:
    frames = _load(ROOT / "frames.json")
    sample = _load(ROOT / "sample.json")
    details = _load(ROOT / "details.json")
    labels = _load(ROOT / "labels.json")
    cases = _load(ROOT / "cases.json")
    sources_lock = _load(ROOT / "sources.lock.json")
    results_lock = _load(ROOT / "results.lock.json")

    assert frames["seed"] == sample["seed"] == SEED
    assert sample["evaluator_commit"] == cases["evaluator_commit"] == EXPECTED_EVALUATOR
    assert [frame["query"] for frame in frames["frames"]] == EXPECTED_QUERIES
    assert [frame["query_frame"] for frame in frames["frames"]] == [1, 2, 3]

    expected_samples: list[dict[str, Any]] = []
    all_candidates: set[tuple[str, int]] = set()
    for frame in frames["frames"]:
        raw_path = ROOT / frame["raw_file"]
        assert _sha256(raw_path) == frame["raw_sha256"]
        candidates = frame["candidates"]
        assert frame["api_returned_count"] == 100
        assert frame["selected_count"] == 25
        assert len(candidates) == frame["unique_after_prior_frames"]
        assert candidates == sorted(candidates, key=lambda item: item["sample_digest"])
        for candidate in candidates:
            key = (candidate["repository"], candidate["pull_request"])
            assert key not in all_candidates
            all_candidates.add(key)
            assert candidate["sample_digest"] == _sample_digest(*key)
        expected_samples.extend(candidates[:25])

    assert len(all_candidates) == 298
    assert sample["sample_size"] == len(sample["samples"]) == len(expected_samples) == 75
    for rank, (observed, expected) in enumerate(
        zip(sample["samples"], expected_samples, strict=True), start=1
    ):
        assert observed["sample_rank"] == rank
        assert {key: value for key, value in observed.items() if key != "sample_rank"} == expected

    sample_identities = [(item["repository"], item["pull_request"]) for item in sample["samples"]]
    assert details["sample_size"] == len(details["details"]) == 75
    assert [
        (item["repository"], item["pull_request"]) for item in details["details"]
    ] == sample_identities
    assert labels["eligibility_blinded_to_parser_output"] is True
    assert labels["sample_size"] == len(labels["labels"]) == 75
    assert [item["rank"] for item in labels["labels"]] == list(range(1, 76))
    assert [
        (item["repository"], item["pull_request"]) for item in labels["labels"]
    ] == sample_identities

    eligible = [item for item in labels["labels"] if item["eligible"]]
    assert len(eligible) == 3
    assert {item["case_id"] for item in eligible} == {item["id"] for item in cases["cases"]}
    assert len({item["repository"] for item in cases["cases"]}) == 3
    assert sum(len(item["claims"]) for item in cases["cases"]) == 15

    expected_source_names: set[str] = set()
    for case in cases["cases"]:
        for path in case["files"]:
            suffix = Path(path).suffix or ".txt"
            for phase in ("before", "after"):
                expected_source_names.add(
                    f"{case['id']}--{path.replace('/', '__')}.{phase}{suffix}"
                )
    assert expected_source_names == set(sources_lock["files"])
    for filename, locked in sources_lock["files"].items():
        assert _sha256(ROOT / "sources" / filename) == locked["sha256"]

    zero_shot_path = ROOT / "results" / "zero-shot-0.18.0.json"
    zero_shot = _load(zero_shot_path)
    locked_zero_shot = results_lock["files"][zero_shot_path.name]
    assert _sha256(zero_shot_path) == locked_zero_shot["sha256"]
    assert zero_shot["phase"] == locked_zero_shot["phase"] == "frozen_zero_shot_0.18.0"
    assert zero_shot["evaluator_commit"] == EXPECTED_EVALUATOR
    assert zero_shot["protocol_sha256"] == _sha256(ROOT / "protocol.md")
    assert zero_shot["sample_sha256"] == _sha256(ROOT / "sample.json")
    assert zero_shot["labels_sha256"] == _sha256(ROOT / "labels.json")
    assert zero_shot["cases_sha256"] == _sha256(ROOT / "cases.json")
    assert zero_shot["sampled_pull_requests"] == 75
    assert zero_shot["eligible_cases"] == 3
    assert zero_shot["selected_claims"] == 15
    assert zero_shot["visible_cases"] == zero_shot["visible_claims"] == 0
    assert zero_shot["source_integrity"] is True

    return {
        "candidates": len(all_candidates),
        "sample": len(sample_identities),
        "eligible": len(eligible),
        "claims": zero_shot["selected_claims"],
        "zero_shot_cases": zero_shot["visible_cases"],
        "zero_shot_claims": zero_shot["visible_claims"],
    }


def main() -> int:
    result = verify()
    print(
        "PASS: prospective study "
        f"candidates={result['candidates']} sample={result['sample']} "
        f"eligible={result['eligible']} zero-shot-cases={result['zero_shot_cases']}/"
        f"{result['eligible']} zero-shot-claims={result['zero_shot_claims']}/"
        f"{result['claims']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
