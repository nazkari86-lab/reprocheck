from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
SEED = "reprocheck-upstream-v2"
QUERIES = [
    '"incorrect benchmark" in:title,body is:merged',
    '"wrong benchmark" in:title,body is:merged',
    '"correct benchmark" in:title,body is:merged',
]


def _gh_api(endpoint: str, fields: dict[str, str] | None = None) -> bytes:
    command = ["gh", "api", "--method", "GET", endpoint]
    for key, value in (fields or {}).items():
        command.extend(["-f", f"{key}={value}"])
    last_error = ""
    for attempt in range(3):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            return completed.stdout
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 2:
            time.sleep(1)
    raise RuntimeError(f"GitHub API failed after 3 attempts: {endpoint}: {last_error}")


def _candidate_key(repository: str, number: int) -> str:
    return f"{repository}#{number}"


def _sample_digest(repository: str, number: int) -> str:
    payload = f"{SEED}|{_candidate_key(repository, number)}".encode()
    return hashlib.sha256(payload).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def retrieve() -> dict[str, Any]:
    raw_dir = ROOT / "raw"
    frames_path = ROOT / "frames.json"
    sample_path = ROOT / "sample.json"
    if frames_path.exists() or sample_path.exists():
        raise FileExistsError("prospective retrieval outputs already exist")
    raw_dir.mkdir(exist_ok=True)
    raw_files = sorted(raw_dir.glob("frame-*.json"))
    if raw_files and len(raw_files) != len(QUERIES):
        raise RuntimeError("partial raw retrieval cannot be resumed safely")
    retrieved_at = (
        (
            datetime.fromtimestamp(min(path.stat().st_mtime for path in raw_files), timezone.utc)
            if raw_files
            else datetime.now(timezone.utc)
        )
        .isoformat()
        .replace("+00:00", "Z")
    )
    assigned: set[str] = set()
    frames: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for frame_index, query in enumerate(QUERIES, start=1):
        raw_path = raw_dir / f"frame-{frame_index}.json"
        if raw_path.exists():
            raw = raw_path.read_bytes()
        else:
            raw = _gh_api("search/issues", {"q": query, "per_page": "100"})
            raw_path.write_bytes(raw)
        payload = json.loads(raw)
        candidates: list[dict[str, Any]] = []
        for item in payload["items"]:
            repository = item["repository_url"].split("repos/", 1)[1]
            number = int(item["number"])
            key = _candidate_key(repository, number)
            if key in assigned:
                continue
            assigned.add(key)
            pull = json.loads(_gh_api(f"repos/{repository}/pulls/{number}"))
            candidates.append(
                {
                    "repository": repository,
                    "pull_request": number,
                    "url": item["html_url"],
                    "title": item["title"],
                    "created_at": item["created_at"],
                    "merged_at": pull["merged_at"],
                    "query_frame": frame_index,
                    "sample_digest": _sample_digest(repository, number),
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
                "unique_after_prior_frames": len(candidates),
                "selected_count": len(selected),
                "raw_file": str(raw_path.relative_to(ROOT)),
                "raw_sha256": _sha256(raw),
                "candidates": candidates,
            }
        )

    frame_document = {
        "schema_version": "reprocheck.upstream-discovery-frames.v1",
        "retrieved_at": retrieved_at,
        "requested_per_query": 100,
        "seed": SEED,
        "frames": frames,
    }
    sample_document = {
        "schema_version": "reprocheck.upstream-discovery-sample.v1",
        "retrieved_at": retrieved_at,
        "evaluator_commit": "2618cad2c54c1610947f4f64e4b7ba8c5302fa28",
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
        "unique_candidates": len(assigned),
        "sample_size": len(samples),
        "frame_counts": [frame["api_returned_count"] for frame in frames],
    }


def main() -> int:
    result = retrieve()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
