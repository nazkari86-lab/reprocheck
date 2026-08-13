from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent


def _gh_json(endpoint: str, *, paginate: bool = False) -> Any:
    command = ["gh", "api", "--method", "GET", endpoint]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    last_error = ""
    for attempt in range(5):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            payload = json.loads(completed.stdout)
            if paginate:
                return [item for page in payload for item in page]
            return payload
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 4:
            time.sleep(2**attempt)
    raise RuntimeError(f"GitHub API failed after 5 attempts: {endpoint}: {last_error}")


def _collect_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    repository = candidate["repository"]
    number = candidate["pull_request"]
    pull = _gh_json(f"repos/{repository}/pulls/{number}")
    merge_commit = _gh_json(f"repos/{repository}/commits/{pull['merge_commit_sha']}")
    files = _gh_json(f"repos/{repository}/pulls/{number}/files?per_page=100", paginate=True)
    parents = merge_commit["parents"]
    if not parents:
        raise RuntimeError(f"merge commit has no parent: {repository}#{number}")
    return {
        **candidate,
        "body": pull.get("body") or "",
        "base_sha_at_open": pull["base"]["sha"],
        "head_sha": pull["head"]["sha"],
        "merge_commit_sha": pull["merge_commit_sha"],
        "merge_parent_sha": parents[0]["sha"],
        "merged_at": pull["merged_at"],
        "changed_files": pull["changed_files"],
        "files_returned": len(files),
        "files": [
            {
                "filename": item["filename"],
                "previous_filename": item.get("previous_filename"),
                "status": item["status"],
                "additions": item["additions"],
                "deletions": item["deletions"],
                "changes": item["changes"],
                "patch": item.get("patch"),
            }
            for item in files
        ],
    }


def _write_checkpoint(path: Path, details: list[dict[str, Any]]) -> None:
    document = {
        "schema_version": "reprocheck.upstream-discovery-details.v5",
        "sample_size": len(details),
        "details": sorted(details, key=lambda item: item["sample_rank"]),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def collect() -> dict[str, int]:
    output = ROOT / "details.json"
    if output.exists():
        raise FileExistsError(output)
    checkpoint = ROOT / "details.partial.json"
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    details = []
    if checkpoint.exists():
        details = json.loads(checkpoint.read_text(encoding="utf-8"))["details"]
    completed_keys = {(item["repository"], item["pull_request"]) for item in details}
    pending = [
        candidate
        for candidate in sample["samples"]
        if (candidate["repository"], candidate["pull_request"]) not in completed_keys
    ]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_collect_candidate, candidate): candidate for candidate in pending
        }
        for future in as_completed(futures):
            candidate = futures[future]
            detail = future.result()
            details.append(detail)
            if len(details) % 10 == 0 or len(details) == sample["sample_size"]:
                _write_checkpoint(checkpoint, details)
            print(
                f"collected {len(details)}/{sample['sample_size']}: "
                f"{candidate['repository']}#{candidate['pull_request']}",
                flush=True,
            )
    _write_checkpoint(output, details)
    checkpoint.unlink(missing_ok=True)
    return {
        "sample_size": len(details),
        "files": sum(len(item["files"]) for item in details),
    }


def main() -> int:
    print(json.dumps(collect(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
