from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
PREREGISTRATION = ROOT / "preregistration.json"
LOCK = ROOT / "preregistration.lock.json"
EVALUATOR = ROOT.parent / "holdout_artifacts" / "evaluator" / "reprocheck-0.7.0-py3-none-any.whl"
MAX_BYTES = 2 * 1024 * 1024
REPOSITORIES = (
    {
        "id": "timm",
        "github": "huggingface/pytorch-image-models",
        "commit": "aa4b5850c1543fa488abf260f18390eda46cf85d",
        "license": "LICENSE",
        "always": ("README.md",),
        "limit": 12,
    },
    {
        "id": "mmsegmentation",
        "github": "open-mmlab/mmsegmentation",
        "commit": "b040e147adfa027bbc071b624bedf0ae84dfc922",
        "license": "LICENSE",
        "always": (),
        "limit": 12,
    },
    {
        "id": "fairseq",
        "github": "facebookresearch/fairseq",
        "commit": "3d262bb25690e4eb2e7d3c1309b1e9c406ca4b99",
        "license": "LICENSE",
        "always": ("README.md",),
        "limit": 12,
    },
    {
        "id": "paddleclas",
        "github": "PaddlePaddle/PaddleClas",
        "commit": "f1233c18455b8acde4fc42ab0bea575fa06daa8e",
        "license": "LICENSE",
        "always": ("README.md",),
        "limit": 12,
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _verify_lock() -> dict[str, Any]:
    lock = _load(LOCK)
    if _sha256(PREREGISTRATION) != lock["preregistration_sha256"]:
        raise ValueError("cross-domain preregistration changed after lock")
    if _sha256(EVALUATOR) != lock["evaluator_sha256"]:
        raise ValueError("frozen v0.7 evaluator changed")
    return lock


def _curl(url: str) -> bytes:
    curl = shutil.which("curl")
    if curl is None:
        raise RuntimeError("curl is required")
    process = subprocess.run(
        [
            curl,
            "--location",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "90",
            "--header",
            "User-Agent: ReproCheck-cross-domain-holdout/1.0",
            url,
        ],
        check=True,
        capture_output=True,
    )
    return process.stdout


def _matches(repository_id: str, path: str) -> bool:
    parts = PurePosixPath(path).parts
    if repository_id == "timm":
        return path == "README.md" or (path.startswith("docs/models/") and path.endswith(".md"))
    if repository_id == "mmsegmentation":
        return len(parts) == 3 and parts[0] == "configs" and parts[-1] == "README.md"
    if repository_id == "fairseq":
        return path == "README.md" or (path.startswith("examples/") and path.endswith("/README.md"))
    if repository_id == "paddleclas":
        return path == "README.md" or (path.startswith("docs/en/models/") and path.endswith(".md"))
    raise ValueError(f"unknown repository: {repository_id}")


def _rank(repository_id: str, path: str) -> str:
    return hashlib.sha256(f"{repository_id}\0{path}".encode()).hexdigest()


def _select(repository: dict[str, Any], tree: list[dict[str, Any]]) -> list[dict[str, str]]:
    blobs = {
        item["path"]: item["sha"]
        for item in tree
        if item.get("type") == "blob" and isinstance(item.get("path"), str)
    }
    candidates = [path for path in blobs if _matches(repository["id"], path)]
    if not candidates:
        raise ValueError(f"registered pattern is empty: {repository['id']}")
    for path in repository["always"]:
        if path not in blobs:
            raise ValueError(f"registered always-include path is missing: {path}")
    sampled = sorted(
        (path for path in candidates if path not in repository["always"]),
        key=lambda path: (_rank(repository["id"], path), path),
    )[: repository["limit"]]
    selected = [*repository["always"], *sampled]
    return [
        {
            "path": path,
            "git_blob_sha": blobs[path],
            "selection_rank_sha256": _rank(repository["id"], path),
        }
        for path in selected
    ]


def _download(repository: dict[str, Any], selection: dict[str, str], kind: str) -> dict[str, Any]:
    path = selection["path"]
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe source path: {path}")
    url = f"https://raw.githubusercontent.com/{repository['github']}/{repository['commit']}/{path}"
    payload = _curl(url)
    if kind == "artifact" and len(payload) > MAX_BYTES:
        raise ValueError(f"artifact exceeds registered byte limit: {path}")
    local_path = Path(repository["id"], *pure.parts)
    destination = SOURCES / local_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {
        "repository": repository["id"],
        "commit": repository["commit"],
        "source_path": path,
        "local_path": local_path.as_posix(),
        "source_url": url,
        "kind": kind,
        "git_blob_sha": selection["git_blob_sha"],
        "selection_rank_sha256": selection["selection_rank_sha256"],
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def fetch() -> dict[str, Any]:
    lock = _verify_lock()
    jobs: list[tuple[dict[str, Any], dict[str, str], str]] = []
    repository_records = []
    for repository in REPOSITORIES:
        tree_url = (
            f"https://api.github.com/repos/{repository['github']}/git/trees/"
            f"{repository['commit']}?recursive=1"
        )
        tree_payload = json.loads(_curl(tree_url))
        if tree_payload.get("truncated"):
            raise ValueError(f"GitHub tree is truncated: {repository['id']}")
        selected = _select(repository, tree_payload.get("tree", []))
        for item in selected:
            jobs.append((repository, item, "artifact"))
        license_sha = next(
            (
                item["sha"]
                for item in tree_payload.get("tree", [])
                if item.get("type") == "blob" and item.get("path") == repository["license"]
            ),
            None,
        )
        if license_sha is None:
            raise ValueError(f"license path missing: {repository['id']}")
        jobs.append(
            (
                repository,
                {
                    "path": repository["license"],
                    "git_blob_sha": license_sha,
                    "selection_rank_sha256": _rank(repository["id"], repository["license"]),
                },
                "license",
            )
        )
        repository_records.append(
            {
                **repository,
                "always": list(repository["always"]),
                "selected_artifacts": len(selected),
            }
        )
    with ThreadPoolExecutor(max_workers=12) as pool:
        entries = list(pool.map(lambda arguments: _download(*arguments), jobs))
    entries.sort(key=lambda item: (item["repository"], item["local_path"]))
    manifest = {
        "schema": "reprocheck.cross-domain-holdout-sources.v1",
        "preregistration_sha256": lock["preregistration_sha256"],
        "evaluator_sha256": lock["evaluator_sha256"],
        "selection_algorithm": "registered SHA-256 path ranking",
        "selection_completed_before_source_content_inspection": True,
        "repositories": repository_records,
        "entries": entries,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify() -> list[str]:
    try:
        lock = _verify_lock()
        manifest = _load(MANIFEST)
    except (KeyError, OSError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        return [str(error)]
    errors: list[str] = []
    if manifest.get("preregistration_sha256") != lock["preregistration_sha256"]:
        errors.append("manifest preregistration binding mismatch")
    if manifest.get("evaluator_sha256") != lock["evaluator_sha256"]:
        errors.append("manifest evaluator binding mismatch")
    expected_paths = set()
    for entry in manifest.get("entries", []):
        local_path = entry.get("local_path")
        if not isinstance(local_path, str):
            errors.append("manifest entry lacks local_path")
            continue
        expected_paths.add(local_path)
        path = SOURCES / local_path
        if not path.is_file():
            errors.append(f"source missing: {local_path}")
            continue
        if path.stat().st_size != entry.get("size_bytes") or _sha256(path) != entry.get("sha256"):
            errors.append(f"source checksum or size mismatch: {local_path}")
    actual_paths = {
        path.relative_to(SOURCES).as_posix() for path in SOURCES.rglob("*") if path.is_file()
    }
    errors.extend(f"unmanifested source: {path}" for path in sorted(actual_paths - expected_paths))
    errors.extend(
        f"manifested source missing: {path}" for path in sorted(expected_paths - actual_paths)
    )
    artifact_count = sum(entry.get("kind") == "artifact" for entry in manifest.get("entries", []))
    license_count = sum(entry.get("kind") == "license" for entry in manifest.get("entries", []))
    repository_artifact_count = sum(
        repository.get("selected_artifacts", 0) for repository in manifest.get("repositories", [])
    )
    if artifact_count != repository_artifact_count or license_count != 4:
        errors.append(
            f"manifest count mismatch: artifacts={artifact_count} licenses={license_count}"
        )
    for repository in manifest.get("repositories", []):
        selected = repository.get("selected_artifacts", 0)
        maximum = repository.get("limit", 0) + len(repository.get("always", []))
        if not 0 < selected <= maximum:
            errors.append(
                f"registered selection limit violated: {repository.get('id')}={selected}/{maximum}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="fetch or verify the v0.7 cross-domain holdout")
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    if args.fetch:
        manifest = fetch()
        print(f"fetched entries={len(manifest['entries'])} manifest={MANIFEST.resolve()}")
    errors = verify()
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PASS: all cross-domain holdout sources match the locked manifest")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
