import copy
import json
from pathlib import Path

import pytest

from reprocheck.ml_acquisition import (
    discover_repositories,
    load_source_frame,
    verify_discovery,
    write_discovery,
)


class FixtureGitHub:
    def __init__(self, results):  # type: ignore[no-untyped-def]
        self.results = results

    def search(self, query: str, *, limit: int):  # type: ignore[no-untyped-def]
        return list(self.results.get(query, []))[:limit]

    def resolve_head(self, full_name: str, default_branch: str) -> str:
        return {"a/vision": "a", "b/nlp": "b", "c/ml": "c"}[full_name] * 40


def _repository(name: str, owner: int, *, stars: int = 10, **changes):  # type: ignore[no-untyped-def]
    value = {
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
    value.update(changes)
    return value


def _frame() -> dict[str, object]:
    return {
        "schema_version": "reprocheck.ml-source-frame.v1",
        "freeze_state": "selection_rules_defined_sources_not_yet_acquired",
        "platform": "GitHub public repositories",
        "snapshot_sort": "stars_descending_then_full_name",
        "maximum_results_per_frame": 100,
        "development_owner_target": 3,
        "recognized_licenses": ["MIT"],
        "search_frames": [
            {"frame_id": "cv", "domain": "computer_vision", "query": "cv"},
            {"frame_id": "nlp", "domain": "nlp", "query": "nlp"},
            {"frame_id": "ml", "domain": "other_ml", "query": "ml"},
        ],
        "one_repository_per_owner": True,
        "forks_allowed": False,
        "required": [],
        "sampling_order": [],
        "selection_must_not_use": [],
        "prospective_exclusion": "owners",
    }


def test_discovery_is_deterministic_owner_disjoint_and_hash_bound(tmp_path: Path) -> None:
    client = FixtureGitHub(
        {
            "cv": [_repository("a/vision", 1, stars=20)],
            "nlp": [_repository("b/nlp", 2), _repository("a/other", 1)],
            "ml": [_repository("c/ml", 3)],
        }
    )
    result = discover_repositories(_frame(), client, retrieved_at="2026-08-21T00:00:00Z")
    assert result["status"] == "target_reached"
    assert [item["repository_id"] for item in result["selected"]] == ["a/vision", "b/nlp", "c/ml"]
    assert any(item["reason"] == "duplicate_owner" for item in result["exclusions"])
    assert verify_discovery(result) == []
    output = tmp_path / "discovery.json"
    write_discovery(result, output)
    assert output.is_file()
    with pytest.raises(ValueError, match="already exists"):
        write_discovery(result, output)


def test_real_source_frame_loads_and_rejects_tamper(tmp_path: Path) -> None:
    frame = load_source_frame(Path("benchmarks/reprocheck_ml_v1/source-frame.json"))
    assert len(frame["search_frames"]) == 3
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        load_source_frame(bad)


def test_discovery_records_all_metadata_exclusions_and_insufficient_status() -> None:
    client = FixtureGitHub(
        {
            "cv": [
                _repository("a/vision", 1),
                _repository("x/fork", 2, fork=True),
                _repository("x/archive", 3, archived=True),
                _repository("x/license", 4, license="NOASSERTION"),
            ],
            "nlp": [_repository("a/vision", 1)],
            "ml": [],
        }
    )
    result = discover_repositories(_frame(), client, retrieved_at="2026-08-21T00:00:00Z")
    assert result["status"] == "insufficient_candidates"
    assert {item["reason"] for item in result["exclusions"]} == {
        "fork",
        "archived",
        "unrecognized_license",
        "duplicate_repository",
    }
    result["selected_owner_count"] = 99
    result["status"] = "target_reached"
    result["discovery_sha256"] = "bad"
    errors = verify_discovery(result)
    assert "ML discovery digest mismatch" in errors
    assert "ML discovery owner count does not match selected records" in errors
    assert "ML discovery status does not match its counts" in errors


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.update(freeze_state="acquired"), "pristine"),
        (lambda frame: frame.update(forks_allowed=True), "forbid forks"),
        (lambda frame: frame.update(maximum_results_per_frame=0), "limits"),
        (lambda frame: frame.update(recognized_licenses=[]), "licenses"),
        (lambda frame: frame.update(search_frames=[]), "three search frames"),
        (
            lambda frame: frame["search_frames"][1].update(frame_id="cv"),
            "frame_id values",
        ),
        (
            lambda frame: frame["search_frames"][0].update(query="reprocheck outcome"),
            "verifier outcome",
        ),
        (lambda frame: frame["search_frames"][0].update(query=""), "non-empty"),
    ],
)
def test_source_frame_guards(tmp_path: Path, mutation, message: str) -> None:
    frame = _frame()
    mutation(frame)
    path = tmp_path / "frame.json"
    path.write_text(json.dumps(frame), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_source_frame(path)


def test_source_frame_loader_rejects_missing_and_array(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot load"):
        load_source_frame(tmp_path / "missing")
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_source_frame(path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item.pop("license"), "unexpected"),
        (lambda item: item.update(full_name=""), "identifiers"),
        (lambda item: item.update(owner_id=0), "positive integer"),
        (lambda item: item.update(stargazers_count=-1), "nonnegative"),
        (lambda item: item.update(fork=1), "flags must be boolean"),
    ],
)
def test_repository_search_item_guards(mutation, message: str) -> None:
    item = _repository("a/vision", 1)
    mutation(item)
    client = FixtureGitHub({"cv": [item], "nlp": [], "ml": []})
    with pytest.raises(ValueError, match=message):
        discover_repositories(_frame(), client, retrieved_at="2026-08-21T00:00:00Z")


def test_discovery_rejects_schema_timestamp_and_commit() -> None:
    with pytest.raises(ValueError, match="unsupported source frame"):
        discover_repositories({}, FixtureGitHub({}))
    with pytest.raises(ValueError, match="ISO-8601"):
        discover_repositories(_frame(), FixtureGitHub({}), retrieved_at="not-a-date")

    class BadCommit(FixtureGitHub):
        def resolve_head(self, full_name: str, default_branch: str) -> str:
            return "bad"

    with pytest.raises(ValueError, match="invalid head commit"):
        discover_repositories(
            _frame(),
            BadCommit({"cv": [_repository("a/vision", 1)], "nlp": [], "ml": []}),
            retrieved_at="2026-08-21T00:00:00Z",
        )


def test_discovery_verifier_rejects_structure_duplicates_reasons_target_and_write(
    tmp_path: Path,
) -> None:
    assert verify_discovery({"schema_version": "bad"}) == [
        "unsupported ML discovery schema",
        "ML discovery selected and exclusions must be arrays",
    ]
    client = FixtureGitHub({"cv": [_repository("a/vision", 1)], "nlp": [], "ml": []})
    result = discover_repositories(_frame(), client, retrieved_at="2026-08-21T00:00:00Z")
    duplicate = copy.deepcopy(result["selected"][0])
    result["selected"].append(duplicate)
    result["exclusions"].append({"reason": "invented"})
    result["target_owner_count"] = 0
    result["discovery_sha256"] = "bad"
    errors = verify_discovery(result)
    assert "ML discovery contains duplicate owners" in errors
    assert "ML discovery contains duplicate repositories" in errors
    assert "ML discovery contains an unsupported exclusion reason" in errors
    assert "ML discovery target owner count is invalid" in errors
    with pytest.raises(ValueError, match="cannot write invalid"):
        write_discovery(result, tmp_path / "bad.json")
