from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
SEED = "reprocheck-upstream-v4"
EVALUATOR_COMMIT = "4b1ffdf633723c2672449aa15198d259f80b7568"
EVALUATOR_VERSION = "0.20.0"
QUERIES = [
    '"correct benchmark results" in:title,body is:merged',
    '"corrected benchmark results" in:title,body is:merged',
    '"fix incorrect benchmark" in:title,body is:merged',
    '"incorrect benchmark result" in:title,body is:merged',
    '"wrong benchmark result" in:title,body is:merged',
    '"fix evaluation results" in:title,body is:merged',
    '"correct evaluation results" in:title,body is:merged',
    '"incorrect evaluation results" in:title,body is:merged',
    '"wrong score" benchmark in:title,body is:merged',
    '"correct score" benchmark in:title,body is:merged',
]
EXPOSURE_FILES = [
    "../upstream_discovery_v3/frames.json",
    "../upstream_discovery_v2/frames.json",
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
    payload = f"{SEED}|{repository}#{pull_request}".encode()
    return hashlib.sha256(payload).hexdigest()


def _add_frames(exposed: set[tuple[str, int]], path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for frame in payload["frames"]:
        for candidate in frame["candidates"]:
            exposed.add(_identity(candidate["repository"], candidate["pull_request"]))


def _prior_exposure() -> set[tuple[str, int]]:
    exposed: set[tuple[str, int]] = set()
    _add_frames(exposed, ROOT / EXPOSURE_FILES[0])
    _add_frames(exposed, ROOT / EXPOSURE_FILES[1])

    snapshot = json.loads((ROOT / EXPOSURE_FILES[2]).read_text(encoding="utf-8"))
    for result in snapshot["results"]:
        exposed.add(_identity(result["repository"], result["pull_request"]))

    manifest = json.loads((ROOT / EXPOSURE_FILES[3]).read_text(encoding="utf-8"))
    for correction in manifest["corrections"]:
        pull_request = int(correction["pull_request"].rstrip("/").rsplit("/", 1)[1])
        exposed.add(_identity(correction["repository"], pull_request))
    return exposed


def retrieve() -> dict[str, Any]:
    raw_dir = ROOT / "raw"
    frames_path = ROOT / "frames.json"
    sample_path = ROOT / "sample.json"
    if frames_path.exists() or sample_path.exists():
        raise FileExistsError("v4 retrieval outputs already exist")
    raw_dir.mkdir(exist_ok=True)

    raw_files = sorted(raw_dir.glob("frame-*.json"))
    if raw_files:
        raise RuntimeError("v4 raw retrieval already started; refusing a mixed-time rerun")
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    exposed = _prior_exposure()
    assigned: set[tuple[str, int]] = set()
    frames: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for frame_index, query in enumerate(QUERIES, start=1):
        raw_path = raw_dir / f"frame-{frame_index}.json"
        raw = _gh_api("search/issues", {"q": query, "per_page": "100"})
        raw_path.write_bytes(raw)
        payload = json.loads(raw)
        candidates: list[dict[str, Any]] = []
        prior_exposure_hits = 0
        duplicate_hits = 0
        for item in payload["items"]:
            repository = item["repository_url"].split("repos/", 1)[1]
            pull_request = int(item["number"])
            identity = _identity(repository, pull_request)
            if identity in exposed:
                prior_exposure_hits += 1
                continue
            if identity in assigned:
                duplicate_hits += 1
                continue
            assigned.add(identity)
            candidates.append(
                {
                    "repository": repository,
                    "pull_request": pull_request,
                    "url": item["html_url"],
                    "title": item["title"],
                    "created_at": item["created_at"],
                    "merged_at": item["pull_request"]["merged_at"],
                    "query_frame": frame_index,
                    "sample_digest": _digest(repository, pull_request),
                }
            )
        candidates.sort(key=lambda candidate: candidate["sample_digest"])
        selected = candidates[:25]
        for candidate in selected:
            samples.append({**candidate, "sample_rank": len(samples) + 1})
        frames.append(
            {
                "query_frame": frame_index,
                "query": query,
                "api_total_count": payload["total_count"],
                "api_returned_count": len(payload["items"]),
                "prior_exposure_hits": prior_exposure_hits,
                "duplicate_hits": duplicate_hits,
                "unique_eligible_for_sampling": len(candidates),
                "selected_count": len(selected),
                "raw_file": str(raw_path.relative_to(ROOT)),
                "raw_sha256": _sha256_bytes(raw),
                "candidates": candidates,
            }
        )

    frame_document = {
        "schema_version": "reprocheck.upstream-discovery-frames.v3",
        "retrieved_at": retrieved_at,
        "requested_per_query": 100,
        "selected_per_frame": 25,
        "seed": SEED,
        "prior_exposure_count": len(exposed),
        "frames": frames,
    }
    sample_document = {
        "schema_version": "reprocheck.upstream-discovery-sample.v3",
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
        "unique_new_candidates": len(assigned),
        "sample_size": len(samples),
        "frame_selected": [frame["selected_count"] for frame in frames],
    }


def main() -> int:
    print(json.dumps(retrieve(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
