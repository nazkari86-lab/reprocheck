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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "bad", "unsupported materialization schema"),
        ("rules_sha256", "bad", "materialization rules digest mismatch"),
        ("corpus_sha256", "bad", "materialization corpus digest mismatch"),
        ("artifact_count", 99, "materialization artifact count mismatch"),
        ("selected_repository_count", 99, "materialization outcome count mismatch"),
        ("excluded_repository_count", 99, "materialization excluded repository count mismatch"),
        ("total_bytes", 99, "materialization total byte count mismatch"),
    ],
)
def test_materialization_verifier_manifest_guards(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    output = tmp_path / field
    materialize_discovery(_discovery(), _rules(), FixtureContents(), output)
    manifest_path = output / "materialization.json"
    manifest = json.loads(manifest_path.read_text())
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert message in verify_materialization(output, _rules())


def test_materialization_verifier_rejects_bad_documents_and_artifacts(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert verify_materialization(missing, _rules())[0].startswith("cannot load materialization")

    output = tmp_path / "arrays"
    materialize_discovery(_discovery(), _rules(), FixtureContents(), output)
    (output / "corpus.json").write_text("[]", encoding="utf-8")
    assert verify_materialization(output, _rules()) == [
        "materialization corpus and manifest must be JSON objects"
    ]

    output = tmp_path / "bad-arrays"
    materialize_discovery(_discovery(), _rules(), FixtureContents(), output)
    corpus_path = output / "corpus.json"
    corpus = json.loads(corpus_path.read_text())
    corpus["repositories"] = None
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
    assert "materialization repositories and outcomes must be arrays" in verify_materialization(
        output, _rules()
    )

    output = tmp_path / "artifacts"
    materialize_discovery(_discovery(), _rules(), FixtureContents(), output)
    corpus_path = output / "corpus.json"
    corpus = json.loads(corpus_path.read_text())
    corpus["repositories"][0]["artifacts"] = [None, {"path": "../unsafe"}, {"path": "sources/gone"}]
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
    errors = verify_materialization(output, _rules())
    assert "materialization artifact descriptor is malformed" in errors
    assert "materialization artifact path is unsafe" in errors
    assert "materialized artifact is missing: sources/gone" in errors


def test_rules_and_selection_cover_all_frozen_boundaries(tmp_path: Path) -> None:
    original = _rules()
    for mutation, message in [
        ({"schema_version": "bad"}, "unsupported"),
        ({"discovery_sha256": "short"}, "bind a discovery"),
        ({"maximum_blob_bytes": 0}, "positive integer"),
        ({"allowed_extensions": []}, "non-empty unique"),
        ({"require_utf8": False}, "must remain true"),
    ]:
        path = tmp_path / f"rules-{len(list(tmp_path.iterdir()))}.json"
        path.write_text(json.dumps({**original, **mutation}), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_materialization_rules(path)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot load"):
        load_materialization_rules(invalid)
    with pytest.raises(ValueError, match="unsafe"):
        artifact_role("../README.md", original)

    entries = [
        {"path": "folder", "type": "tree", "sha": "0" * 40, "size": 0},
        {"path": "REPORT.md", "type": "blob", "sha": "1" * 40, "size": 1},
        {"path": "metrics.csv", "type": "blob", "sha": "2" * 40, "size": 1},
        {"path": "predictions.csv", "type": "blob", "sha": "3" * 40, "size": 1},
        {"path": "docs/evaluation.md", "type": "blob", "sha": "4" * 40, "size": 1},
        {"path": "results.txt", "type": "blob", "sha": "5" * 40, "size": 9_999_999},
    ]
    selected, exclusions = select_tree_artifacts(
        {"truncated": False, "entries": entries}, {**original, "maximum_artifacts_per_repository": 2}
    )
    assert len(selected) == 2
    assert {item["reason"] for item in exclusions} == {"artifact_limit", "oversized_blob"}
    assert artifact_role("docs/guide.md", original) == "report"


def test_materialization_repository_and_download_failures_are_explicit(tmp_path: Path) -> None:
    discovery = _discovery()
    discovery["selected"] = []
    with pytest.raises(ValueError, match="no repositories"):
        materialize_discovery(discovery, _rules(), FixtureContents(), tmp_path / "empty")

    class BadTree(FixtureContents):
        def tree(self, full_name: str, commit_sha: str):  # type: ignore[no-untyped-def]
            return {"truncated": True, "entries": []}

    result = materialize_discovery(_discovery(), _rules(), BadTree(), tmp_path / "bad-tree")
    assert result["excluded_repository_count"] == 1

    discovery = _discovery()
    selected = discovery["selected"]
    assert isinstance(selected, list) and isinstance(selected[0], dict)
    selected[0]["repository_id"] = "///"
    with pytest.raises(ValueError, match="empty local path"):
        materialize_discovery(discovery, _rules(), FixtureContents(), tmp_path / "bad-id")

    class WrongSize(FixtureContents):
        def blob(self, full_name: str, blob_sha: str) -> bytes:
            return super().blob(full_name, blob_sha) + b"x"

    with pytest.raises(ValueError, match="size mismatch"):
        materialize_discovery(_discovery(), _rules(), WrongSize(), tmp_path / "wrong-size")

    rules = {**_rules(), "maximum_total_bytes": 1}
    with pytest.raises(ValueError, match="total byte limit"):
        materialize_discovery(_discovery(), rules, FixtureContents(), tmp_path / "too-large")
