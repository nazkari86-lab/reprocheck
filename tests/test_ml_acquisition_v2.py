from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from reprocheck.ml_acquisition_v2 import (
    discover_balanced_repositories,
    validate_source_frame_v2,
    verify_balanced_discovery,
)


def _frame() -> dict[str, object]:
    return json.loads(Path("benchmarks/reprocheck_ml_v1/source-frame-v2.json").read_text())


def _repo(name: str, owner: int, stars: int = 10) -> dict[str, object]:
    return {
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "owner_id": owner,
        "owner_login": name.split("/")[0],
        "fork": False,
        "archived": False,
        "license": "MIT",
        "default_branch": "main",
        "stargazers_count": stars,
    }


class Fixture:
    def __init__(self) -> None:
        self.results = {
            "topic:computer-vision language:Python stars:>=10 archived:false fork:false": [
                _repo("cv/a", 1),
                _repo("cv/b", 2),
            ],
            "topic:natural-language-processing language:Python stars:>=10 archived:false fork:false": [
                _repo("nlp/a", 3),
                _repo("nlp/b", 4),
            ],
            "topic:machine-learning language:Python stars:>=10 archived:false fork:false": [
                _repo("ml/a", 5),
                _repo("ml/b", 6),
            ],
        }

    def search(self, query: str, *, limit: int):  # type: ignore[no-untyped-def]
        return self.results[query][:limit]

    def resolve_head(self, full_name: str, default_branch: str) -> str:
        return str("abcdef"[sum(map(ord, full_name)) % 6]) * 40


def test_balanced_discovery_requires_and_reaches_each_domain_quota() -> None:
    frame = _frame()
    frame["development_owner_target"] = 6
    frame["domain_owner_targets"] = {"computer_vision": 2, "nlp": 2, "other_ml": 2}
    result = discover_balanced_repositories(frame, Fixture(), retrieved_at="2026-08-21T00:00:00Z")
    assert result["status"] == "target_reached"
    assert result["domain_owner_counts"] == frame["domain_owner_targets"]
    assert result["selected_owner_count"] == 6
    assert verify_balanced_discovery(result) == []


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.update(schema_version="bad"), "unexpected"),
        (lambda frame: frame.update(freeze_state="acquired"), "pristine"),
        (lambda frame: frame.update(forks_allowed=True), "reject forks"),
        (lambda frame: frame.update(domain_owner_targets={"nlp": 1}), "three domain"),
        (lambda frame: frame["domain_owner_targets"].update(nlp=0), "positive"),
        (lambda frame: frame.update(development_owner_target=999), "sum"),
        (lambda frame: frame.update(search_frames=frame["search_frames"][:2]), "one frame"),
        (lambda frame: frame.update(maximum_results_per_frame=0), "limit"),
        (lambda frame: frame.update(recognized_licenses=[]), "licenses"),
        (lambda frame: frame.update(supersedes_discovery_sha256="bad"), "superseded"),
    ],
)
def test_v2_source_frame_guards(mutation, message: str) -> None:
    frame = _frame()
    mutation(frame)
    with pytest.raises(ValueError, match=message):
        validate_source_frame_v2(frame)


def test_balanced_discovery_reports_insufficient_and_verifier_tamper() -> None:
    frame = _frame()
    frame["development_owner_target"] = 6
    frame["domain_owner_targets"] = {"computer_vision": 2, "nlp": 2, "other_ml": 2}
    client = Fixture()
    client.results[next(reversed(client.results))] = []
    result = discover_balanced_repositories(frame, client, retrieved_at="2026-08-21T00:00:00Z")
    assert result["status"] == "insufficient_candidates"
    result["selected"].append(copy.deepcopy(result["selected"][0]))
    result["domain_owner_counts"]["nlp"] = 99
    result["selected_owner_count"] = 99
    result["status"] = "target_reached"
    result["discovery_sha256"] = "bad"
    errors = verify_balanced_discovery(result)
    assert "balanced discovery contains duplicate owners" in errors
    assert "balanced discovery contains duplicate repositories" in errors
    assert "balanced discovery domain counts do not match selected records" in errors
    assert "balanced discovery owner count does not match" in errors
    assert "balanced discovery digest mismatch" in errors


def test_balanced_discovery_exclusions_timestamp_commit_and_verifier_structure() -> None:
    frame = _frame()
    frame["development_owner_target"] = 3
    frame["domain_owner_targets"] = {"computer_vision": 1, "nlp": 1, "other_ml": 1}
    with pytest.raises(ValueError, match="ISO-8601"):
        discover_balanced_repositories(frame, Fixture(), retrieved_at="bad")

    client = Fixture()
    query = next(iter(client.results))
    client.results[query] = [
        {**_repo("bad/fork", 10), "fork": True},
        {**_repo("bad/archive", 11), "archived": True},
        {**_repo("bad/license", 12), "license": "NOASSERTION"},
        _repo("cv/a", 1),
    ]
    client.results[list(client.results)[1]].insert(0, _repo("cv/a", 1))
    result = discover_balanced_repositories(frame, client, retrieved_at="2026-08-21T00:00:00Z")
    assert {item["reason"] for item in result["exclusions"]} >= {
        "fork",
        "archived",
        "unrecognized_license",
        "duplicate_repository",
    }

    class BadCommit(Fixture):
        def resolve_head(self, full_name: str, default_branch: str) -> str:
            return "bad"

    with pytest.raises(ValueError, match="invalid head commit"):
        discover_balanced_repositories(frame, BadCommit(), retrieved_at="2026-08-21T00:00:00Z")

    assert verify_balanced_discovery({}) == [
        "unsupported balanced discovery schema",
        "balanced discovery selected and exclusions must be arrays",
    ]
    result["exclusions"].append({"reason": "invented"})
    result["status"] = "insufficient_candidates"
    result["discovery_sha256"] = "bad"
    errors = verify_balanced_discovery(result)
    assert "balanced discovery contains an unsupported exclusion reason" in errors
    assert "balanced discovery status does not match domain quotas" in errors
