from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from .ml_contracts import canonical_contract_json


MATERIALIZATION_SCHEMA = "reprocheck.ml-materialization.v1"


class RepositoryContents(Protocol):
    def tree(self, full_name: str, commit_sha: str) -> dict[str, Any]: ...

    def blob(self, full_name: str, blob_sha: str) -> bytes: ...


def load_materialization_rules(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load materialization rules: {path}") from error
    required = {
        "schema_version",
        "discovery_sha256",
        "maximum_blob_bytes",
        "maximum_artifacts_per_repository",
        "maximum_total_bytes",
        "allowed_extensions",
        "report_basenames",
        "evidence_terms",
        "preferred_directories",
        "excluded_directories",
        "require_complete_git_tree",
        "require_utf8",
        "require_report_artifact",
        "selection_boundary",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("materialization rules have unexpected or missing fields")
    if payload["schema_version"] != "reprocheck.ml-materialization-rules.v1":
        raise ValueError("unsupported materialization rules schema")
    digest = payload["discovery_sha256"]
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("materialization rules must bind a discovery SHA-256")
    for name in ("maximum_blob_bytes", "maximum_artifacts_per_repository", "maximum_total_bytes"):
        if not isinstance(payload[name], int) or payload[name] < 1:
            raise ValueError(f"materialization rule {name} must be a positive integer")
    for name in (
        "allowed_extensions",
        "report_basenames",
        "evidence_terms",
        "preferred_directories",
        "excluded_directories",
    ):
        values = payload[name]
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ValueError(f"materialization rule {name} must be a non-empty unique array")
    for name in ("require_complete_git_tree", "require_utf8", "require_report_artifact"):
        if payload[name] is not True:
            raise ValueError(f"materialization rule {name} must remain true")
    return payload


def _safe_git_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe Git tree path: {value}")
    return path


def _normalized_stem(path: PurePosixPath) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.casefold()).strip("-")


def artifact_role(path: str, rules: dict[str, Any]) -> str | None:
    parsed = _safe_git_path(path)
    suffix = parsed.suffix.casefold()
    if suffix not in rules["allowed_extensions"]:
        return None
    lowered_parts = tuple(part.casefold() for part in parsed.parts)
    if any(part in rules["excluded_directories"] for part in lowered_parts[:-1]):
        return None
    stem = _normalized_stem(parsed)
    evidence = any(term in stem for term in rules["evidence_terms"])
    if suffix == ".csv" and evidence:
        return "predictions" if "prediction" in stem else "metrics"
    if suffix == ".json" and evidence:
        return "metrics"
    if suffix in {".md", ".rst", ".txt", ".html", ".ipynb"}:
        if stem in rules["report_basenames"] or parsed.name.casefold().startswith("readme"):
            return "report"
        if evidence or any(part in rules["preferred_directories"] for part in lowered_parts[:-1]):
            return "report"
    return None


def _priority(path: str, role: str, rules: dict[str, Any]) -> tuple[int, int, str]:
    parsed = PurePosixPath(path)
    stem = _normalized_stem(parsed)
    if len(parsed.parts) == 1 and parsed.name.casefold().startswith("readme"):
        band = 0
    elif stem in rules["report_basenames"]:
        band = 1
    elif role == "metrics":
        band = 2
    elif role == "predictions":
        band = 3
    elif any(part.casefold() in rules["preferred_directories"] for part in parsed.parts[:-1]):
        band = 4
    else:
        band = 5
    return band, len(parsed.parts), path.casefold()


def select_tree_artifacts(
    tree: dict[str, Any], rules: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if (
        set(tree) != {"truncated", "entries"}
        or not isinstance(tree["truncated"], bool)
        or not isinstance(tree["entries"], list)
    ):
        raise ValueError("Git tree payload is malformed")
    if tree["truncated"] and rules["require_complete_git_tree"]:
        raise ValueError("Git tree is truncated")
    selected: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    for entry in tree["entries"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "type", "sha", "size"}:
            raise ValueError("Git tree entry is malformed")
        path = str(entry["path"])
        if entry["type"] != "blob":
            continue
        role = artifact_role(path, rules)
        if role is None:
            continue
        size = entry["size"]
        if not isinstance(size, int) or size < 0:
            raise ValueError("Git blob size is invalid")
        if size > rules["maximum_blob_bytes"]:
            exclusions.append({"path": path, "reason": "oversized_blob"})
            continue
        sha = str(entry["sha"])
        if len(sha) != 40 or any(character not in "0123456789abcdef" for character in sha):
            raise ValueError("Git blob SHA is invalid")
        selected.append({"path": path, "role": role, "blob_sha": sha, "size": size})
    selected.sort(key=lambda item: _priority(item["path"], item["role"], rules))
    limit = rules["maximum_artifacts_per_repository"]
    for item in selected[limit:]:
        exclusions.append({"path": item["path"], "reason": "artifact_limit"})
    return selected[:limit], sorted(exclusions, key=lambda item: (item["path"], item["reason"]))


def _safe_local_repository_id(repository_id: str) -> str:
    value = re.sub(r"[^a-z0-9._-]+", "__", repository_id.casefold()).strip("._-")
    if not value:
        raise ValueError("repository_id cannot map to an empty local path")
    return value


def materialize_discovery(
    discovery: dict[str, Any], rules: dict[str, Any], client: RepositoryContents, output_dir: Path
) -> dict[str, Any]:
    if output_dir.exists():
        raise ValueError(f"materialization output already exists: {output_dir}")
    if (
        discovery.get("schema_version") != "reprocheck.ml-discovery.v2"
        or discovery.get("status") != "target_reached"
    ):
        raise ValueError("materialization requires a successful v2 discovery")
    if discovery.get("discovery_sha256") != rules["discovery_sha256"]:
        raise ValueError("materialization rules bind a different discovery")
    repositories = discovery.get("selected")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("materialization discovery contains no repositories")
    temporary = Path(tempfile.mkdtemp(prefix="reprocheck-ml-materialization-"))
    source_root = temporary / "sources"
    corpus_repositories: list[dict[str, Any]] = []
    repository_outcomes: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        for repository in repositories:
            repository_id = str(repository["repository_id"])
            full_name = repository_id
            commit_sha = str(repository["commit_sha"])
            tree = client.tree(full_name, commit_sha)
            try:
                candidates, path_exclusions = select_tree_artifacts(tree, rules)
            except ValueError as error:
                repository_outcomes.append(
                    {
                        "repository_id": repository_id,
                        "status": "excluded",
                        "reason": str(error),
                        "path_exclusions": [],
                    }
                )
                continue
            if rules["require_report_artifact"] and not any(
                item["role"] == "report" for item in candidates
            ):
                repository_outcomes.append(
                    {
                        "repository_id": repository_id,
                        "status": "excluded",
                        "reason": "no_report_artifact",
                        "path_exclusions": path_exclusions,
                    }
                )
                continue
            artifacts = []
            local_repository = _safe_local_repository_id(repository_id)
            for candidate in candidates:
                data = client.blob(full_name, candidate["blob_sha"])
                if len(data) != candidate["size"]:
                    raise ValueError(f"Git blob size mismatch: {repository_id}:{candidate['path']}")
                if rules["require_utf8"]:
                    try:
                        data.decode("utf-8")
                    except UnicodeDecodeError:
                        path_exclusions.append({"path": candidate["path"], "reason": "non_utf8"})
                        continue
                if total_bytes + len(data) > rules["maximum_total_bytes"]:
                    raise ValueError("materialization exceeds the frozen total byte limit")
                relative = PurePosixPath(
                    "sources", local_repository, *_safe_git_path(candidate["path"]).parts
                )
                target = temporary.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                total_bytes += len(data)
                artifacts.append(
                    {
                        "artifact_id": f"{repository_id}:{candidate['path']}",
                        "path": relative.as_posix(),
                        "role": candidate["role"],
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size_bytes": len(data),
                    }
                )
            if rules["require_report_artifact"] and not any(
                item["role"] == "report" for item in artifacts
            ):
                shutil.rmtree(source_root / local_repository, ignore_errors=True)
                repository_outcomes.append(
                    {
                        "repository_id": repository_id,
                        "status": "excluded",
                        "reason": "no_report_artifact",
                        "path_exclusions": path_exclusions,
                    }
                )
                continue
            corpus_repositories.append(
                {
                    "repository_id": repository_id,
                    "owner_id": repository["owner_id"],
                    "commit_sha": commit_sha,
                    "source_url": repository["source_url"],
                    "retrieved_at": discovery["retrieved_at"],
                    "license": repository["license"],
                    "domain": repository["domain"],
                    "language": "und",
                    "lineage_id": repository_id,
                    "is_fork": False,
                    "artifacts": artifacts,
                }
            )
            repository_outcomes.append(
                {
                    "repository_id": repository_id,
                    "status": "included",
                    "reason": None,
                    "path_exclusions": path_exclusions,
                    "artifact_count": len(artifacts),
                }
            )
        corpus = {
            "schema_version": "reprocheck.ml-corpus.v1",
            "corpus_id": f"reprocheck-ml-development-{discovery['discovery_sha256'][:12]}",
            "created_at": discovery["retrieved_at"],
            "repositories": corpus_repositories,
        }
        manifest: dict[str, Any] = {
            "schema_version": MATERIALIZATION_SCHEMA,
            "status": "materialized",
            "discovery_sha256": discovery["discovery_sha256"],
            "rules_sha256": hashlib.sha256(canonical_contract_json(rules).encode()).hexdigest(),
            "selected_repository_count": len(repositories),
            "included_repository_count": len(corpus_repositories),
            "excluded_repository_count": len(repositories) - len(corpus_repositories),
            "artifact_count": sum(len(item["artifacts"]) for item in corpus_repositories),
            "total_bytes": total_bytes,
            "repository_outcomes": repository_outcomes,
            "corpus_sha256": hashlib.sha256(canonical_contract_json(corpus).encode()).hexdigest(),
            "materialization_sha256": "",
        }
        manifest["materialization_sha256"] = hashlib.sha256(
            canonical_contract_json(manifest).encode()
        ).hexdigest()
        (temporary / "corpus.json").write_text(
            canonical_contract_json(corpus) + "\n", encoding="utf-8"
        )
        (temporary / "materialization.json").write_text(
            canonical_contract_json(manifest) + "\n", encoding="utf-8"
        )
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temporary), output_dir)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_materialization(output_dir: Path, rules: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        corpus = json.loads((output_dir / "corpus.json").read_text(encoding="utf-8"))
        manifest = json.loads((output_dir / "materialization.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"cannot load materialization: {error}"]
    if not isinstance(corpus, dict) or not isinstance(manifest, dict):
        return ["materialization corpus and manifest must be JSON objects"]
    if manifest.get("schema_version") != MATERIALIZATION_SCHEMA:
        errors.append("unsupported materialization schema")
    unsigned = {**manifest, "materialization_sha256": ""}
    expected_manifest = hashlib.sha256(canonical_contract_json(unsigned).encode()).hexdigest()
    if manifest.get("materialization_sha256") != expected_manifest:
        errors.append("materialization digest mismatch")
    expected_rules = hashlib.sha256(canonical_contract_json(rules).encode()).hexdigest()
    if manifest.get("rules_sha256") != expected_rules:
        errors.append("materialization rules digest mismatch")
    expected_corpus = hashlib.sha256(canonical_contract_json(corpus).encode()).hexdigest()
    if manifest.get("corpus_sha256") != expected_corpus:
        errors.append("materialization corpus digest mismatch")
    repositories = corpus.get("repositories")
    outcomes = manifest.get("repository_outcomes")
    if not isinstance(repositories, list) or not isinstance(outcomes, list):
        errors.append("materialization repositories and outcomes must be arrays")
        return errors
    artifacts = [
        artifact
        for repository in repositories
        if isinstance(repository, dict)
        for artifact in repository.get("artifacts", [])
    ]
    if manifest.get("included_repository_count") != len(repositories):
        errors.append("materialization included repository count mismatch")
    if manifest.get("artifact_count") != len(artifacts):
        errors.append("materialization artifact count mismatch")
    if manifest.get("selected_repository_count") != len(outcomes):
        errors.append("materialization outcome count mismatch")
    if manifest.get("excluded_repository_count") != sum(
        item.get("status") == "excluded" for item in outcomes if isinstance(item, dict)
    ):
        errors.append("materialization excluded repository count mismatch")
    expected_paths: set[str] = set()
    total_bytes = 0
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("materialization artifact descriptor is malformed")
            continue
        try:
            relative = _safe_git_path(str(artifact["path"]))
        except (KeyError, ValueError):
            errors.append("materialization artifact path is unsafe")
            continue
        path = output_dir.joinpath(*relative.parts)
        expected_paths.add(relative.as_posix())
        if not path.is_file():
            errors.append(f"materialized artifact is missing: {relative.as_posix()}")
            continue
        data = path.read_bytes()
        total_bytes += len(data)
        if len(data) != artifact.get("size_bytes") or hashlib.sha256(
            data
        ).hexdigest() != artifact.get("sha256"):
            errors.append(f"materialized artifact integrity mismatch: {relative.as_posix()}")
    source_dir = output_dir / "sources"
    actual_paths = (
        {
            path.relative_to(output_dir).as_posix()
            for path in source_dir.rglob("*")
            if path.is_file()
        }
        if source_dir.exists()
        else set()
    )
    if actual_paths != expected_paths:
        errors.append("materialization contains missing or unregistered source files")
    if manifest.get("total_bytes") != total_bytes:
        errors.append("materialization total byte count mismatch")
    return errors
