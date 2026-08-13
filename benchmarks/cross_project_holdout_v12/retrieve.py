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
BENCHMARKS = ROOT.parent
SEED = "reprocheck-cross-project-v12-independent"
EVALUATOR_COMMIT = "0b52adad8061d77e355a200dee88b7522252f292"
EVALUATOR_VERSION = "0.26.0"
SELECTED_PER_FRAME = 2
QUERIES = [
    '"benchmark results" filename:README.md extension:md',
    '"performance results" filename:README.md extension:md',
    '"experimental results" filename:README.md extension:md',
    '"evaluation results" filename:README.md extension:md',
    '"performance benchmark" filename:README.md extension:md',
    '"benchmark table" filename:README.md extension:md',
    '"latency (ms)" filename:README.md extension:md',
    '"latency ms" "throughput" filename:README.md extension:md',
    '"requests/sec" filename:README.md extension:md',
    '"ops/sec" "benchmark" filename:README.md extension:md',
    '"rows/s" "memory" filename:README.md extension:md',
    '"tokens/s" "latency" filename:README.md extension:md',
    '"F1-score" "accuracy" filename:README.md extension:md',
    '"ROC-AUC" "F1" filename:README.md extension:md',
    '"precision recall F1" filename:README.md extension:md',
    '"mAP@0.5" filename:README.md extension:md',
    '"PSNR" "SSIM" filename:README.md extension:md',
    '"BLEU-4" "METEOR" filename:README.md extension:md',
    '"MRR@10" filename:README.md extension:md',
    '"NDCG@10" filename:README.md extension:md',
    '"mean absolute error" "R2" filename:README.md extension:md',
    '"RMSE" "R-squared" filename:README.md extension:md',
    '"compression ratio" "throughput" filename:README.md extension:md',
    '"peak memory" "runtime" filename:README.md extension:md',
    '"benchmark" filename:PERFORMANCE.md extension:md',
    '"results" filename:PERFORMANCE.md extension:md',
    '"latency" filename:PERFORMANCE.md extension:md',
    '"benchmark" filename:BENCHMARK.md extension:md',
    '"results" filename:BENCHMARK.md extension:md',
    '"throughput" filename:BENCHMARK.md extension:md',
    '"results" filename:EVALUATION.md extension:md',
    '"metrics" filename:EVALUATION.md extension:md',
    '"benchmark results" path:docs extension:md',
    '"performance comparison" path:docs extension:md',
    '"evaluation metrics" path:docs extension:md',
    '"test summary" path:docs extension:md',
]


def _run(command: list[str]) -> bytes:
    last_error = ""
    for attempt in range(8):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            return completed.stdout
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 7:
            time.sleep(min(60, 2**attempt))
    raise RuntimeError(f"command failed after eight attempts: {last_error}")


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


def _record_repositories(payload: Any, repositories: set[str]) -> None:
    if isinstance(payload, dict):
        repository = payload.get("repository")
        if isinstance(repository, str) and "/" in repository:
            repositories.add(repository.casefold())
        for value in payload.values():
            _record_repositories(value, repositories)
    elif isinstance(payload, list):
        for value in payload:
            _record_repositories(value, repositories)


def _prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories: set[str] = set()
    roots = [
        *[BENCHMARKS / f"upstream_discovery_v{version}" for version in range(2, 10)],
        BENCHMARKS / "upstream_corrections",
        BENCHMARKS / "cross_project_holdout_v10",
        BENCHMARKS / "cross_project_holdout_v11",
    ]
    for root in roots:
        for name in ("frames.json", "sample.json", "manifest.json", "discovery_snapshot.json"):
            path = root / name
            if path.exists():
                _record_repositories(json.loads(path.read_text(encoding="utf-8")), repositories)
    return repositories, {repository.split("/", 1)[0] for repository in repositories}


def retrieve() -> dict[str, Any]:
    outputs = [ROOT / "raw", ROOT / "sources", ROOT / "frames.json", ROOT / "sample.json"]
    if any(path.exists() for path in outputs):
        raise FileExistsError("v12 retrieval outputs already exist")
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
        "schema_version": "reprocheck.cross-project-frames.v12",
        "retrieved_at": retrieved_at,
        "seed": SEED,
        "selected_per_frame": SELECTED_PER_FRAME,
        "global_owner_cap": 1,
        "prior_repository_count": len(prior_repositories),
        "frames": frames,
    }
    sample_document = {
        "schema_version": "reprocheck.cross-project-sample.v12",
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
