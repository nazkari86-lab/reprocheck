from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
SEED = "reprocheck-cross-project-v11-independent"
EVALUATOR_COMMIT = "792ad73"
EVALUATOR_VERSION = "0.25.0"
SELECTED_PER_FRAME = 2
QUERIES = [
    '"benchmark summary" filename:README.md extension:md',
    '"results summary" filename:README.md extension:md',
    '"test results" filename:README.md extension:md',
    '"our results" filename:README.md extension:md',
    '"performance comparison" filename:README.md extension:md',
    '"benchmark comparison" filename:README.md extension:md',
    '"evaluation metrics" filename:README.md extension:md',
    '"average latency" filename:README.md extension:md',
    '"mean latency" "throughput" filename:README.md extension:md',
    '"req/sec" filename:README.md extension:md',
    '"operations per second" filename:README.md extension:md',
    '"samples/sec" filename:README.md extension:md',
    '"GPU memory" "results" filename:README.md extension:md',
    '"peak RSS" filename:README.md extension:md',
    '"macro F1" "accuracy" filename:README.md extension:md',
    '"weighted F1" "results" filename:README.md extension:md',
    '"specificity" "sensitivity" filename:README.md extension:md',
    '"AUPRC" "AUROC" filename:README.md extension:md',
    '"perplexity" "results" filename:README.md extension:md',
    '"METEOR" "BLEU" filename:README.md extension:md',
    '"nDCG@" "MRR" filename:README.md extension:md',
    '"hit rate" "benchmark" filename:README.md extension:md',
    '"mean absolute error" "results" filename:README.md extension:md',
    '"RMSE" "MAE" filename:README.md extension:md',
    '"frames per second" "benchmark" filename:README.md extension:md',
    '"compression ratio" "benchmark" filename:README.md extension:md',
    '"benchmark" filename:RESULTS.md extension:md',
    '"accuracy" filename:RESULTS.md extension:md',
    '"latency" filename:RESULTS.md extension:md',
    '"benchmark" filename:BENCHMARKS.md extension:md',
    '"results" filename:BENCHMARKS.md extension:md',
    '"throughput" filename:BENCHMARKS.md extension:md',
]


def _run(command: list[str]) -> bytes:
    last_error = ""
    for attempt in range(7):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            return completed.stdout
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 6:
            time.sleep(min(60, 2**attempt))
    raise RuntimeError(f"command failed after seven attempts: {last_error}")


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
    for relative in ("discovery_snapshot.json", "manifest.json"):
        path = ROOT.parent / "upstream_corrections" / relative
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("results", payload.get("corrections", [])):
            repositories.add(item["repository"].casefold())
    v10_sample = ROOT.parent / "cross_project_holdout_v10" / "sample.json"
    for item in json.loads(v10_sample.read_text(encoding="utf-8"))["samples"]:
        repositories.add(item["repository"].casefold())
    return repositories, {repository.split("/", 1)[0] for repository in repositories}


def retrieve() -> dict[str, Any]:
    outputs = [ROOT / "raw", ROOT / "sources", ROOT / "frames.json", ROOT / "sample.json"]
    if any(path.exists() for path in outputs):
        raise FileExistsError("v11 retrieval outputs already exist")
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
            candidates.append(
                {
                    "repository": repository,
                    "owner": repository.split("/", 1)[0],
                    "path": item["path"],
                    "blob_sha": item["sha"],
                    "blob_api_url": item["git_url"],
                    "html_url": item["html_url"],
                    "query_frame": index,
                    "sample_digest": _digest(repository, item["path"], item["sha"]),
                }
            )
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
            content = base64.b64decode(blob["content"])
            if len(content) > 250_000 or b"\x00" in content:
                continue
            source_name = f"sample-{len(samples) + 1:02d}.md"
            (ROOT / "sources" / source_name).write_bytes(content)
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
        frames.append(
            {
                "query_frame": index,
                "query": query,
                "api_total_count": payload.get("total_count", 0),
                "api_returned_count": len(payload.get("items", [])),
                "raw_file": str(raw_path.relative_to(ROOT)),
                "raw_sha256": _sha256(raw),
                "selected_count": len(selected),
                "candidates": candidates,
            }
        )

    frame_document = {
        "schema_version": "reprocheck.cross-project-frames.v11",
        "retrieved_at": retrieved_at,
        "seed": SEED,
        "selected_per_frame": SELECTED_PER_FRAME,
        "global_owner_cap": 1,
        "prior_repository_count": len(prior_repositories),
        "frames": frames,
    }
    sample_document = {
        "schema_version": "reprocheck.cross-project-sample.v11",
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
