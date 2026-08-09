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
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
REPOSITORIES = (
    {
        "id": "monai_model_zoo",
        "github": "Project-MONAI/model-zoo",
        "commit": "b9e4d04bb2a073110bde9e5c05c9690241e938b6",
        "license_path": "LICENSE",
        "expected_artifacts": 35,
        "selection": "all models/*/configs/metadata.json files",
    },
    {
        "id": "transformers",
        "github": "huggingface/transformers",
        "commit": "e8ea728a3eeeb903e77c7d1bd29267c80a1be71f",
        "license_path": "LICENSE",
        "expected_artifacts": 18,
        "selection": "all examples/pytorch/**/README.md files",
    },
    {
        "id": "tensorflow_docs",
        "github": "tensorflow/docs",
        "commit": "35e0922e059d7bc6d515a83e03a7494f0640c314",
        "license_path": "LICENSE",
        "expected_artifacts": 7,
        "selection": "all site/en/tutorials/keras/*.ipynb files",
    },
)


def _curl(url: str) -> bytes:
    executable = shutil.which("curl")
    if executable is None:
        raise RuntimeError("curl is required for certificate-verified source fetching")
    process = subprocess.run(
        [
            executable,
            "--location",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "60",
            "--header",
            "User-Agent: ReproCheck-real-artifact-fetcher/1.0",
            url,
        ],
        check=True,
        capture_output=True,
    )
    return process.stdout


def _selected_paths(repository: dict[str, Any], tree: list[dict[str, Any]]) -> list[str]:
    paths = [item["path"] for item in tree if item.get("type") == "blob"]
    repository_id = repository["id"]
    if repository_id == "monai_model_zoo":
        selected = [
            path
            for path in paths
            if path.startswith("models/")
            and path.endswith("/configs/metadata.json")
            and len(PurePosixPath(path).parts) == 4
        ]
    elif repository_id == "transformers":
        selected = [
            path
            for path in paths
            if path.startswith("examples/pytorch/") and path.endswith("README.md")
        ]
    elif repository_id == "tensorflow_docs":
        selected = [
            path
            for path in paths
            if path.startswith("site/en/tutorials/keras/")
            and path.endswith(".ipynb")
            and len(PurePosixPath(path).parts) == 5
        ]
    else:  # pragma: no cover - fixed registry makes this unreachable
        raise ValueError(f"unknown repository id: {repository_id}")
    selected = sorted(selected)
    if len(selected) != repository["expected_artifacts"]:
        raise RuntimeError(
            f"selection drift for {repository_id}: expected "
            f"{repository['expected_artifacts']}, found {len(selected)}"
        )
    return selected


def _download(repository: dict[str, Any], path: str, kind: str) -> dict[str, Any]:
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ValueError(f"unsafe source path: {path}")
    url = f"https://raw.githubusercontent.com/{repository['github']}/{repository['commit']}/{path}"
    payload = _curl(url)
    local_path = Path(repository["id"]) / Path(*pure_path.parts)
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
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def fetch() -> dict[str, Any]:
    jobs: list[tuple[dict[str, Any], str, str]] = []
    for repository in REPOSITORIES:
        tree_url = (
            f"https://api.github.com/repos/{repository['github']}/git/trees/"
            f"{repository['commit']}?recursive=1"
        )
        tree_payload = json.loads(_curl(tree_url))
        if tree_payload.get("truncated"):
            raise RuntimeError(f"GitHub tree was truncated for {repository['id']}")
        for path in _selected_paths(repository, tree_payload.get("tree", [])):
            jobs.append((repository, path, "artifact"))
        jobs.append((repository, repository["license_path"], "license"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(lambda arguments: _download(*arguments), jobs))
    entries.sort(key=lambda item: (item["repository"], item["local_path"]))
    manifest = {
        "schema": "reprocheck.real-artifact-sources.v1",
        "selection_is_exhaustive_within_declared_patterns": True,
        "repositories": list(REPOSITORIES),
        "entries": entries,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify() -> list[str]:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"source manifest cannot be read: {error}"]
    errors: list[str] = []
    expected_paths = set()
    for entry in manifest.get("entries", []):
        local_path = entry.get("local_path")
        if not isinstance(local_path, str):
            errors.append("manifest entry has no local_path")
            continue
        expected_paths.add(local_path)
        path = SOURCES / local_path
        if not path.is_file():
            errors.append(f"source is missing: {local_path}")
            continue
        payload = path.read_bytes()
        if len(payload) != entry.get("size_bytes"):
            errors.append(f"source size mismatch: {local_path}")
        if hashlib.sha256(payload).hexdigest() != entry.get("sha256"):
            errors.append(f"source checksum mismatch: {local_path}")
    actual_paths = {
        path.relative_to(SOURCES).as_posix() for path in SOURCES.rglob("*") if path.is_file()
    }
    for unexpected in sorted(actual_paths - expected_paths):
        errors.append(f"unmanifested source: {unexpected}")
    for missing in sorted(expected_paths - actual_paths):
        errors.append(f"manifested source is absent: {missing}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="download pinned sources")
    args = parser.parse_args()
    if args.fetch:
        manifest = fetch()
        print(f"fetched={len(manifest['entries'])} manifest={MANIFEST}")
    errors = verify()
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PASS: all frozen real-artifact sources match their manifest")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
