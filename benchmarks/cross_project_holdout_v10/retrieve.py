from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
SEED = "reprocheck-cross-project-v10"
EVALUATOR_COMMIT = "734a3d5b4ec421bcccacede69df4f86f7c1900fe"
EVALUATOR_VERSION = "0.24.0"
SELECTED_PER_FRAME = 2
QUERIES = [
    '"benchmark results" filename:README.md extension:md',
    '"evaluation results" filename:README.md extension:md',
    '"performance results" filename:README.md extension:md',
    '"experimental results" filename:README.md extension:md',
    '"accuracy" "precision" "recall" filename:README.md extension:md',
    '"F1 score" "results" filename:README.md extension:md',
    '"mAP" "benchmark" filename:README.md extension:md',
    '"latency" "throughput" filename:README.md extension:md',
    '"requests/sec" filename:README.md extension:md',
    '"tokens/s" "benchmark" filename:README.md extension:md',
    '"memory usage" "benchmark" filename:README.md extension:md',
    '"tests passed" filename:README.md extension:md',
    '"pass rate" "evaluation" filename:README.md extension:md',
    '"BLEU" "results" filename:README.md extension:md',
    '"WER" "results" filename:README.md extension:md',
    '"ROUGE" "results" filename:README.md extension:md',
    '"Dice" "IoU" filename:README.md extension:md',
    '"AUROC" "results" filename:README.md extension:md',
    '"recall@" "precision@" filename:README.md extension:md',
    '"P@5" "R@5" filename:README.md extension:md',
    '"execution time" "results" filename:README.md extension:md',
    '"peak memory" "results" filename:README.md extension:md',
    '"success rate" "benchmark" filename:README.md extension:md',
    '"test coverage" "passed" filename:README.md extension:md',
]


def _run(command: list[str]) -> bytes:
    last_error = ""
    for attempt in range(5):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            return completed.stdout
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 4:
            time.sleep(2**attempt)
    raise RuntimeError(f"command failed after five attempts: {last_error}")


def _gh_api(endpoint: str, fields: dict[str, str] | None = None) -> bytes:
    command = ["gh", "api", "--method", "GET", endpoint]
    for key, value in (fields or {}).items():
        command.extend(["-f", f"{key}={value}"])
    return _run(command)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(repository: str, path: str, blob_sha: str) -> str:
    identity = f"{repository.casefold()}|{path}|{blob_sha}"
    return hashlib.sha256(f"{SEED}|{identity}".encode()).hexdigest()


def _prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories: set[str] = set()
    for version in range(2, 10):
        path = ROOT.parent / f"upstream_discovery_v{version}" / "frames.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for frame in payload["frames"]:
            for candidate in frame["candidates"]:
                repositories.add(candidate["repository"].casefold())
    snapshot = ROOT.parent / "upstream_corrections" / "discovery_snapshot.json"
    if snapshot.exists():
        for item in json.loads(snapshot.read_text(encoding="utf-8"))["results"]:
            repositories.add(item["repository"].casefold())
    manifest = ROOT.parent / "upstream_corrections" / "manifest.json"
    if manifest.exists():
        for item in json.loads(manifest.read_text(encoding="utf-8"))["corrections"]:
            repositories.add(item["repository"].casefold())
    return repositories, {repository.split("/", 1)[0] for repository in repositories}


def retrieve() -> dict[str, Any]:
    outputs = [ROOT / "raw", ROOT / "sources", ROOT / "frames.json", ROOT / "sample.json"]
    if any(path.exists() for path in outputs):
        raise FileExistsError("v10 retrieval outputs already exist")
    (ROOT / "raw").mkdir()
    (ROOT / "sources").mkdir()
    prior_repositories, prior_owners = _prior_repositories_and_owners()
    selected_repositories: set[str] = set()
    selected_owners: set[str] = set()
    seen_blobs: set[tuple[str, str, str]] = set()
    frames: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for index, query in enumerate(QUERIES, start=1):
        raw = _gh_api("search/code", {"q": query, "per_page": "100"})
        raw_path = ROOT / "raw" / f"frame-{index}.json"
        raw_path.write_bytes(raw)
        payload = json.loads(raw)
        candidates: list[dict[str, Any]] = []
        for item in payload.get("items", []):
            repository = item["repository"]["full_name"]
            identity = (repository.casefold(), item["path"], item["sha"])
            if identity in seen_blobs:
                continue
            seen_blobs.add(identity)
            candidates.append({
                "repository": repository,
                "owner": repository.split("/", 1)[0],
                "path": item["path"],
                "blob_sha": item["sha"],
                "blob_api_url": item["git_url"],
                "html_url": item["html_url"],
                "query_frame": index,
                "sample_digest": _digest(repository, item["path"], item["sha"]),
            })
        candidates.sort(key=lambda candidate: candidate["sample_digest"])
        selected: list[dict[str, Any]] = []
        for candidate in candidates:
            repository_key = candidate["repository"].casefold()
            owner_key = candidate["owner"].casefold()
            if repository_key in prior_repositories or owner_key in prior_owners:
                continue
            if repository_key in selected_repositories or owner_key in selected_owners:
                continue
            blob = json.loads(_gh_api(candidate["blob_api_url"]))
            content = __import__("base64").b64decode(blob["content"])
            if len(content) > 250_000 or b"\x00" in content:
                continue
            source_name = f"sample-{len(samples) + 1:02d}.md"
            source_path = ROOT / "sources" / source_name
            source_path.write_bytes(content)
            enriched = {
                **candidate,
                "sample_rank": len(samples) + 1,
                "source_file": f"sources/{source_name}",
                "source_sha256": _sha256(content),
                "source_bytes": len(content),
            }
            selected_repositories.add(repository_key)
            selected_owners.add(owner_key)
            selected.append(enriched)
            samples.append(enriched)
            if len(selected) == SELECTED_PER_FRAME:
                break
        frames.append({
            "query_frame": index,
            "query": query,
            "api_total_count": payload.get("total_count", 0),
            "api_returned_count": len(payload.get("items", [])),
            "raw_file": str(raw_path.relative_to(ROOT)),
            "raw_sha256": _sha256(raw),
            "selected_count": len(selected),
            "candidates": candidates,
        })

    frame_document = {
        "schema_version": "reprocheck.cross-project-frames.v10",
        "retrieved_at": retrieved_at,
        "seed": SEED,
        "selected_per_frame": SELECTED_PER_FRAME,
        "global_owner_cap": 1,
        "prior_repository_count": len(prior_repositories),
        "frames": frames,
    }
    sample_document = {
        "schema_version": "reprocheck.cross-project-sample.v10",
        "retrieved_at": retrieved_at,
        "evaluator_commit": EVALUATOR_COMMIT,
        "evaluator_version": EVALUATOR_VERSION,
        "sample_size": len(samples),
        "samples": samples,
    }
    (ROOT / "frames.json").write_text(json.dumps(frame_document, indent=2, sort_keys=True) + "\n")
    (ROOT / "sample.json").write_text(json.dumps(sample_document, indent=2, sort_keys=True) + "\n")
    return {
        "retrieved_at": retrieved_at,
        "sample_size": len(samples),
        "independent_owners": len(selected_owners),
        "frame_selected": [frame["selected_count"] for frame in frames],
    }


if __name__ == "__main__":
    print(json.dumps(retrieve(), sort_keys=True))
