from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
SEED = "reprocheck-upstream-v5"
EVALUATOR_COMMIT = "96e0a4688ef74e6ddc41ec78471276954c5cda66"
EVALUATOR_VERSION = "0.21.0"
SELECTED_PER_FRAME = 20
BASE = "is:pr is:merged created:>=2024-01-01 in:title,body"
QUERIES = [
    f'"corrected benchmark" {BASE}',
    f'"fix benchmark results" {BASE}',
    f'"incorrect benchmark results" {BASE}',
    f'"wrong benchmark results" {BASE}',
    f'"stale benchmark results" {BASE}',
    f'"recompute benchmark results" {BASE}',
    f'"update benchmark numbers" {BASE}',
    f'"correct performance numbers" {BASE}',
    f'"fix performance results" {BASE}',
    f'"corrected latency" {BASE}',
    f'"correct memory usage" {BASE}',
    f'"incorrect accuracy" {BASE}',
    f'"corrected accuracy" {BASE}',
    f'"incorrect recall" {BASE}',
    f'"corrected recall" {BASE}',
    f'"incorrect precision" {BASE}',
    f'"corrected score" {BASE}',
    f'"fix metrics table" {BASE}',
    f'"sync benchmark results" {BASE}',
    f'"results did not match" benchmark {BASE}',
    f'"ground truth correction" results {BASE}',
    f'"evaluation bug" results {BASE}',
    f'"measurement bug" benchmark {BASE}',
    f'"documentation benchmark results" fix {BASE}',
]
EXPOSURE_FILES = [
    "../upstream_discovery_v2/frames.json",
    "../upstream_discovery_v3/frames.json",
    "../upstream_discovery_v4/frames.json",
    "../upstream_corrections/discovery_snapshot.json",
    "../upstream_corrections/manifest.json",
]


def _gh_api(endpoint: str, fields: dict[str, str]) -> bytes:
    command = ["gh", "api", "--method", "GET", endpoint]
    for key, value in fields.items():
        command.extend(["-f", f"{key}={value}"])
    last_error = ""
    for attempt in range(5):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            return completed.stdout
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 4:
            time.sleep(2**attempt)
    raise RuntimeError(f"GitHub API failed after 5 attempts: {last_error}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(repository: str, pull_request: int) -> tuple[str, int]:
    return repository.casefold(), int(pull_request)


def _digest(repository: str, pull_request: int) -> str:
    return hashlib.sha256(f"{SEED}|{repository}#{pull_request}".encode()).hexdigest()


def _add_frames(exposed: set[tuple[str, int]], path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for frame in payload["frames"]:
        for candidate in frame["candidates"]:
            exposed.add(_identity(candidate["repository"], candidate["pull_request"]))


def _prior_exposure() -> set[tuple[str, int]]:
    exposed: set[tuple[str, int]] = set()
    for relative in EXPOSURE_FILES[:3]:
        _add_frames(exposed, ROOT / relative)
    snapshot = json.loads((ROOT / EXPOSURE_FILES[3]).read_text(encoding="utf-8"))
    for result in snapshot["results"]:
        exposed.add(_identity(result["repository"], result["pull_request"]))
    manifest = json.loads((ROOT / EXPOSURE_FILES[4]).read_text(encoding="utf-8"))
    for correction in manifest["corrections"]:
        number = int(correction["pull_request"].rstrip("/").rsplit("/", 1)[1])
        exposed.add(_identity(correction["repository"], number))
    return exposed


def retrieve() -> dict[str, Any]:
    raw_dir = ROOT / "raw"
    frames_path = ROOT / "frames.json"
    sample_path = ROOT / "sample.json"
    if frames_path.exists() or sample_path.exists() or raw_dir.exists():
        raise FileExistsError("v5 retrieval outputs already exist")
    raw_dir.mkdir()
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    exposed = _prior_exposure()
    selected_repositories: set[str] = set()
    selected_owners: set[str] = set()
    seen_this_study: set[tuple[str, int]] = set()
    frames: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for frame_index, query in enumerate(QUERIES, start=1):
        raw = _gh_api("search/issues", {"q": query, "per_page": "100"})
        raw_path = raw_dir / f"frame-{frame_index}.json"
        raw_path.write_bytes(raw)
        payload = json.loads(raw)
        candidates: list[dict[str, Any]] = []
        prior_hits = duplicate_hits = 0
        for item in payload["items"]:
            repository = item["repository_url"].split("repos/", 1)[1]
            number = int(item["number"])
            identity = _identity(repository, number)
            if identity in exposed:
                prior_hits += 1
                continue
            if identity in seen_this_study:
                duplicate_hits += 1
                continue
            seen_this_study.add(identity)
            candidates.append(
                {
                    "repository": repository,
                    "pull_request": number,
                    "url": item["html_url"],
                    "title": item["title"],
                    "created_at": item["created_at"],
                    "merged_at": item["pull_request"]["merged_at"],
                    "query_frame": frame_index,
                    "sample_digest": _digest(repository, number),
                }
            )
        candidates.sort(key=lambda candidate: candidate["sample_digest"])
        selected: list[dict[str, Any]] = []
        owner_cap_hits = repository_cap_hits = 0
        for candidate in candidates:
            repository_key = candidate["repository"].casefold()
            owner_key = repository_key.split("/", 1)[0]
            if repository_key in selected_repositories:
                repository_cap_hits += 1
                continue
            if owner_key in selected_owners:
                owner_cap_hits += 1
                continue
            selected_repositories.add(repository_key)
            selected_owners.add(owner_key)
            selected.append(candidate)
            samples.append({**candidate, "sample_rank": len(samples) + 1})
            if len(selected) == SELECTED_PER_FRAME:
                break
        frames.append(
            {
                "query_frame": frame_index,
                "query": query,
                "api_total_count": payload["total_count"],
                "api_returned_count": len(payload["items"]),
                "prior_exposure_hits": prior_hits,
                "duplicate_hits": duplicate_hits,
                "repository_cap_hits": repository_cap_hits,
                "owner_cap_hits": owner_cap_hits,
                "unique_candidates": len(candidates),
                "selected_count": len(selected),
                "raw_file": str(raw_path.relative_to(ROOT)),
                "raw_sha256": _sha256_bytes(raw),
                "candidates": candidates,
            }
        )
    frame_document = {
        "schema_version": "reprocheck.upstream-discovery-frames.v4",
        "retrieved_at": retrieved_at,
        "requested_per_query": 100,
        "selected_per_frame": SELECTED_PER_FRAME,
        "seed": SEED,
        "prior_exposure_count": len(exposed),
        "global_owner_cap": 1,
        "global_repository_cap": 1,
        "frames": frames,
    }
    sample_document = {
        "schema_version": "reprocheck.upstream-discovery-sample.v4",
        "retrieved_at": retrieved_at,
        "evaluator_commit": EVALUATOR_COMMIT,
        "evaluator_version": EVALUATOR_VERSION,
        "seed": SEED,
        "sample_size": len(samples),
        "samples": samples,
    }
    frames_path.write_text(
        json.dumps(frame_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    sample_path.write_text(
        json.dumps(sample_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "retrieved_at": retrieved_at,
        "prior_exposure_count": len(exposed),
        "unique_new_candidates": len(seen_this_study),
        "sample_size": len(samples),
        "independent_owners": len(selected_owners),
        "frame_selected": [frame["selected_count"] for frame in frames],
    }


def main() -> int:
    print(json.dumps(retrieve(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
