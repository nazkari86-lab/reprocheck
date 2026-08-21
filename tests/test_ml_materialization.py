from __future__ import annotations

import json
from pathlib import Path

import pytest

from reprocheck.ml_materialization import (
    artifact_role,
    load_materialization_rules,
    materialize_discovery,
    select_tree_artifacts,
    verify_materialization,
)


def _rules() -> dict[str, object]:
    return json.loads(Path("benchmarks/reprocheck_ml_v1/materialization-rules-v1.json").read_text())


def _discovery() -> dict[str, object]:
    rules = _rules()
    return {
        "schema_version": "reprocheck.ml-discovery.v2",
        "status": "target_reached",
        "retrieved_at": "2026-08-21T00:00:00Z",
        "discovery_sha256": rules["discovery_sha256"],
        "selected": [
            {
                "repository_id": "owner/project",
                "owner_id": "github:1",
                "commit_sha": "a" * 40,
                "source_url": "https://github.com/owner/project",
                "license": "MIT",
                "domain": "computer_vision",
            }
        ],
    }


class FixtureContents:
    blobs = {
        "1" * 40: b"# Results\nAccuracy: 94%\n",
        "2" * 40: b'{"accuracy": 0.94}\n',
    }

    def tree(self, full_name: str, commit_sha: str):  # type: ignore[no-untyped-def]
        return {
            "truncated": False,
            "entries": [
                {
                    "path": "README.md",
                    "type": "blob",
                    "sha": "1" * 40,
                    "size": len(self.blobs["1" * 40]),
                },
                {
                    "path": "results/metrics.json",
                    "type": "blob",
                    "sha": "2" * 40,
                    "size": len(self.blobs["2" * 40]),
                },
                {"path": "src/model.py", "type": "blob", "sha": "3" * 40, "size": 10},
            ],
        }

    def blob(self, full_name: str, blob_sha: str) -> bytes:
        return self.blobs[blob_sha]


def test_materialization_builds_hash_bound_corpus_and_verifies(tmp_path: Path) -> None:
    rules = _rules()
    output = tmp_path / "materialized"
    result = materialize_discovery(_discovery(), rules, FixtureContents(), output)
    assert result["included_repository_count"] == 1
    assert result["artifact_count"] == 2
    assert verify_materialization(output, rules) == []
    corpus = json.loads((output / "corpus.json").read_text())
    assert [item["role"] for item in corpus["repositories"][0]["artifacts"]] == [
        "report",
        "metrics",
    ]
    with pytest.raises(ValueError, match="already exists"):
        materialize_discovery(_discovery(), rules, FixtureContents(), output)


def test_path_roles_and_deterministic_tree_selection() -> None:
    rules = _rules()
    assert artifact_role("README.md", rules) == "report"
    assert artifact_role("results/predictions.csv", rules) == "predictions"
    assert artifact_role("results/metrics.json", rules) == "metrics"
    assert artifact_role("src/model.py", rules) is None
    assert artifact_role("vendor/results.md", rules) is None
    tree = FixtureContents().tree("owner/project", "a" * 40)
    selected, exclusions = select_tree_artifacts(tree, rules)
    assert [item["path"] for item in selected] == ["README.md", "results/metrics.json"]
    assert exclusions == []


def test_tree_rejects_truncation_malformed_entries_size_and_sha() -> None:
    rules = _rules()
    with pytest.raises(ValueError, match="truncated"):
        select_tree_artifacts({"truncated": True, "entries": []}, rules)
    with pytest.raises(ValueError, match="payload"):
        select_tree_artifacts({}, rules)
    for entry, message in [
        ({"bad": True}, "entry"),
        ({"path": "README.md", "type": "blob", "sha": "1" * 40, "size": -1}, "size"),
        ({"path": "README.md", "type": "blob", "sha": "bad", "size": 1}, "SHA"),
    ]:
        with pytest.raises(ValueError, match=message):
            select_tree_artifacts({"truncated": False, "entries": [entry]}, rules)


def test_rules_loader_and_materialization_contract_guards(tmp_path: Path) -> None:
    assert (
        load_materialization_rules(
            Path("benchmarks/reprocheck_ml_v1/materialization-rules-v1.json")
        )["require_utf8"]
        is True
    )
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        load_materialization_rules(bad)
    rules = _rules()
    discovery = _discovery()
    discovery["status"] = "failed"
    with pytest.raises(ValueError, match="successful v2"):
        materialize_discovery(discovery, rules, FixtureContents(), tmp_path / "one")
    discovery = _discovery()
    discovery["discovery_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="different discovery"):
        materialize_discovery(discovery, rules, FixtureContents(), tmp_path / "two")


def test_materialization_excludes_no_report_and_cleans_non_utf8(tmp_path: Path) -> None:
    class NoReport(FixtureContents):
        blobs = {"2" * 40: b'{"accuracy": 0.94}\n'}

        def tree(self, full_name: str, commit_sha: str):  # type: ignore[no-untyped-def]
            return {
                "truncated": False,
                "entries": [
                    {
                        "path": "metrics.json",
                        "type": "blob",
                        "sha": "2" * 40,
                        "size": len(self.blobs["2" * 40]),
                    }
                ],
            }

    output = tmp_path / "no-report"
    result = materialize_discovery(_discovery(), _rules(), NoReport(), output)
    assert result["included_repository_count"] == 0
    assert result["excluded_repository_count"] == 1
    assert verify_materialization(output, _rules()) == []

    class NonUtf8(FixtureContents):
        blobs = {"1" * 40: b"\xff"}

        def tree(self, full_name: str, commit_sha: str):  # type: ignore[no-untyped-def]
            return {
                "truncated": False,
                "entries": [{"path": "README.md", "type": "blob", "sha": "1" * 40, "size": 1}],
            }

    output = tmp_path / "non-utf8"
    result = materialize_discovery(_discovery(), _rules(), NonUtf8(), output)
    assert result["included_repository_count"] == 0
    assert not (output / "sources").exists()


def test_materialization_verifier_detects_tamper_and_unregistered_file(tmp_path: Path) -> None:
    output = tmp_path / "materialized"
    materialize_discovery(_discovery(), _rules(), FixtureContents(), output)
    source = next((output / "sources").rglob("README.md"))
    source.write_text("tampered", encoding="utf-8")
    extra = output / "sources" / "extra.txt"
    extra.write_text("extra", encoding="utf-8")
    errors = verify_materialization(output, _rules())
    assert any("integrity mismatch" in error for error in errors)
    assert "materialization contains missing or unregistered source files" in errors
    manifest = json.loads((output / "materialization.json").read_text())
    manifest["included_repository_count"] = 99
    (output / "materialization.json").write_text(json.dumps(manifest), encoding="utf-8")
    errors = verify_materialization(output, _rules())
    assert "materialization digest mismatch" in errors
    assert "materialization included repository count mismatch" in errors
