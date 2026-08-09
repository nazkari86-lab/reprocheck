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
PREREGISTRATION_LOCK = ROOT / "preregistration.lock.json"
EVALUATOR = (
    PROJECT
    / "benchmarks"
    / "challenge_artifacts"
    / "evaluator"
    / "reprocheck-0.6.0-py3-none-any.whl"
)
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
REPOSITORIES = (
    {
        "id": "ultralytics",
        "github": "ultralytics/ultralytics",
        "default_branch": "main",
        "commit": "80b1f58432dff7f9ef9d89b9551e990704e1f820",
        "license_path": "LICENSE",
        "expected_artifacts": 22,
        "selection": "README.md and all top-level docs/en/models/*.md files",
    },
    {
        "id": "yolov5",
        "github": "ultralytics/yolov5",
        "default_branch": "master",
        "commit": "20d1d78a08277e365d57bfa3a2cce752772d9e59",
        "license_path": "LICENSE",
        "expected_artifacts": 1,
        "selection": "README.md",
    },
    {
        "id": "detr",
        "github": "facebookresearch/detr",
        "default_branch": "main",
        "commit": "29901c51d7fe8712168b8d0d64351170bc0f83e0",
        "license_path": "LICENSE",
        "expected_artifacts": 1,
        "selection": "README.md",
    },
    {
        "id": "yolox",
        "github": "Megvii-BaseDetection/YOLOX",
        "default_branch": "main",
        "commit": "6ddff4824372906469a7fae2dc3206c7aa4bbaee",
        "license_path": "LICENSE",
        "expected_artifacts": 1,
        "selection": "README.md",
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_lock() -> dict[str, Any]:
    lock = json.loads(PREREGISTRATION_LOCK.read_text(encoding="utf-8"))
    if _sha256(PREREGISTRATION) != lock["preregistration_sha256"]:
        raise RuntimeError("preregistration changed after it was locked")
    if not EVALUATOR.is_file() or _sha256(EVALUATOR) != lock["evaluator_sha256"]:
        raise RuntimeError("frozen holdout evaluator is missing or changed")
    return lock


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
            "User-Agent: ReproCheck-preregistered-holdout-fetcher/1.0",
            url,
        ],
        check=True,
        capture_output=True,
    )
    return process.stdout


def _selected_paths(repository: dict[str, Any], tree: list[dict[str, Any]]) -> list[str]:
    paths = [item["path"] for item in tree if item.get("type") == "blob"]
    if repository["id"] == "ultralytics":
        selected = [
            path
            for path in paths
            if path == "README.md"
            or (
                path.startswith("docs/en/models/")
                and path.endswith(".md")
                and len(PurePosixPath(path).parts) == 4
            )
        ]
    else:
        selected = [path for path in paths if path == "README.md"]
    selected = sorted(selected)
    if len(selected) != repository["expected_artifacts"]:
        raise RuntimeError(
            f"selection drift for {repository['id']}: expected "
            f"{repository['expected_artifacts']}, found {len(selected)}"
        )
    return selected


def _download(repository: dict[str, Any], path: str, kind: str) -> dict[str, Any]:
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ValueError(f"unsafe source path: {path}")
    url = f"https://raw.githubusercontent.com/{repository['github']}/{repository['commit']}/{path}"
    payload = _curl(url)
    if kind == "artifact" and len(payload) > MAX_ARTIFACT_BYTES:
        raise RuntimeError(f"artifact exceeds preregistered size limit: {path}")
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
    lock = _verify_lock()
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

    with ThreadPoolExecutor(max_workers=12) as pool:
        entries = list(pool.map(lambda arguments: _download(*arguments), jobs))
    entries.sort(key=lambda item: (item["repository"], item["local_path"]))
    manifest = {
        "schema": "reprocheck.preregistered-holdout-sources.v1",
        "preregistration_sha256": lock["preregistration_sha256"],
        "evaluator_sha256": lock["evaluator_sha256"],
        "selection_is_exhaustive_within_declared_patterns": True,
        "selection_locked_before_source_download": True,
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
        lock = _verify_lock()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (KeyError, OSError, json.JSONDecodeError, RuntimeError) as error:
        return [f"holdout lock or source manifest cannot be verified: {error}"]
    errors: list[str] = []
    if manifest.get("preregistration_sha256") != lock["preregistration_sha256"]:
        errors.append("manifest preregistration hash mismatch")
    if manifest.get("evaluator_sha256") != lock["evaluator_sha256"]:
        errors.append("manifest evaluator hash mismatch")
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
        if entry.get("kind") == "artifact" and len(payload) > MAX_ARTIFACT_BYTES:
            errors.append(f"artifact exceeds preregistered size limit: {local_path}")
    actual_paths = {
        path.relative_to(SOURCES).as_posix() for path in SOURCES.rglob("*") if path.is_file()
    }
    for unexpected in sorted(actual_paths - expected_paths):
        errors.append(f"unmanifested source: {unexpected}")
    for missing in sorted(expected_paths - actual_paths):
        errors.append(f"manifested source is absent: {missing}")
    artifact_count = sum(entry.get("kind") == "artifact" for entry in manifest.get("entries", []))
    license_count = sum(entry.get("kind") == "license" for entry in manifest.get("entries", []))
    if artifact_count != 25 or license_count != 4:
        errors.append(
            f"manifest count mismatch: artifacts={artifact_count}, licenses={license_count}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="download pinned holdout sources")
    args = parser.parse_args()
    if args.fetch:
        manifest = fetch()
        print(f"fetched={len(manifest['entries'])} manifest={MANIFEST}")
    errors = verify()
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PASS: all preregistered holdout sources match their manifest")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
