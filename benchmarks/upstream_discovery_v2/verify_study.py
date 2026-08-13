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
    summary = _load(ROOT / "study-summary.json")

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

    development_path = ROOT / "results" / "development-current.json"
    development = _load(development_path)
    locked_development = results_lock["files"][development_path.name]
    assert _sha256(development_path) == locked_development["sha256"]
    assert development["phase"] == locked_development["phase"] == "development_after_zero_shot"
    assert development["protocol_sha256"] == zero_shot["protocol_sha256"]
    assert development["sample_sha256"] == zero_shot["sample_sha256"]
    assert development["labels_sha256"] == zero_shot["labels_sha256"]
    assert development["cases_sha256"] == zero_shot["cases_sha256"]
    assert development["sampled_pull_requests"] == zero_shot["sampled_pull_requests"]
    assert development["eligible_cases"] == zero_shot["eligible_cases"]
    assert development["selected_claims"] == zero_shot["selected_claims"]
    assert development["visible_cases"] == development["eligible_cases"] == 3
    assert development["visible_claims"] == development["selected_claims"] == 15
    assert development["source_integrity"] is True
    assert development["evaluation_role"] == "post_inspection_development"
    assert development["implementation_binding"] == "source tree committed with this result"
    assert development["evaluator_version"] == "0.19.0"
    assert (
        development["evaluator_commit_role"] == "frozen baseline used for the zero-shot comparison"
    )

    assert summary["retrieval"] == {
        "query_frames": 3,
        "unique_candidates": 298,
        "deterministic_sample": 75,
        "adjudicated": 75,
    }
    assert summary["eligible"]["cases"] == development["eligible_cases"]
    assert summary["eligible"]["selected_claims"] == development["selected_claims"]
    assert summary["eligible"]["repositories"] == len(
        {item["repository"] for item in cases["cases"]}
    )
    assert summary["eligible"]["independent_owners"] == len(
        {item["repository"].split("/", 1)[0] for item in cases["cases"]}
    )
    assert summary["eligible"]["immutable_files"] == len(sources_lock["files"])
    assert summary["frozen_zero_shot"]["cases_visible"] == zero_shot["visible_cases"]
    assert summary["frozen_zero_shot"]["claims_visible"] == zero_shot["visible_claims"]
    assert summary["post_inspection_development"]["cases_visible"] == development["visible_cases"]
    assert summary["post_inspection_development"]["claims_visible"] == development["visible_claims"]
    assert summary["independently_frozen_raw_evidence"]["cases"] == 0
    assert summary["independently_frozen_raw_evidence"]["agreement_rate"] is None

    return {
        "candidates": len(all_candidates),
        "sample": len(sample_identities),
        "eligible": len(eligible),
        "claims": zero_shot["selected_claims"],
        "zero_shot_cases": zero_shot["visible_cases"],
        "zero_shot_claims": zero_shot["visible_claims"],
        "development_cases": development["visible_cases"],
        "development_claims": development["visible_claims"],
    }


def main() -> int:
    result = verify()
    print(
        "PASS: prospective study "
        f"candidates={result['candidates']} sample={result['sample']} "
        f"eligible={result['eligible']} zero-shot-cases={result['zero_shot_cases']}/"
        f"{result['eligible']} zero-shot-claims={result['zero_shot_claims']}/"
        f"{result['claims']} development-cases={result['development_cases']}/"
        f"{result['eligible']} development-claims={result['development_claims']}/"
        f"{result['claims']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
