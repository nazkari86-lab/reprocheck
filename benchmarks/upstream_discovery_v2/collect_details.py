from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent


def _gh_json(endpoint: str, fields: dict[str, str] | None = None) -> Any:
    command = ["gh", "api", "--method", "GET", endpoint]
    for key, value in (fields or {}).items():
        command.extend(["-f", f"{key}={value}"])
    last_error = ""
    for attempt in range(3):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            return json.loads(completed.stdout)
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 2:
            time.sleep(1)
    raise RuntimeError(f"GitHub API failed after 3 attempts: {endpoint}: {last_error}")


def collect() -> dict[str, int]:
    output = ROOT / "details.json"
    if output.exists():
        raise FileExistsError(output)
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    details: list[dict[str, Any]] = []
    for candidate in sample["samples"]:
        repository = candidate["repository"]
        number = candidate["pull_request"]
        pull = _gh_json(f"repos/{repository}/pulls/{number}")
        files = _gh_json(f"repos/{repository}/pulls/{number}/files", {"per_page": "100"})
        details.append(
            {
                **candidate,
                "body": pull.get("body") or "",
                "base_sha": pull["base"]["sha"],
                "head_sha": pull["head"]["sha"],
                "merge_commit_sha": pull["merge_commit_sha"],
                "merged_at": pull["merged_at"],
                "changed_files": pull["changed_files"],
                "files": [
                    {
                        "filename": item["filename"],
                        "status": item["status"],
                        "additions": item["additions"],
                        "deletions": item["deletions"],
                        "changes": item["changes"],
                        "patch": item.get("patch"),
                    }
                    for item in files
                ],
            }
        )
    document = {
        "schema_version": "reprocheck.upstream-discovery-details.v1",
        "sample_size": len(details),
        "details": details,
    }
    output.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "sample_size": len(details),
        "files": sum(len(item["files"]) for item in details),
    }


def main() -> int:
    print(json.dumps(collect(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
