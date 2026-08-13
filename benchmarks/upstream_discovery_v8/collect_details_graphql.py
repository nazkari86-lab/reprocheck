from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "upstream_discovery_v5" / "collect_details.py"


def graphql(query: str, variables: dict[str, object]) -> dict[str, Any]:
    command = ["gh", "api", "graphql", "-f", f"query={query}"]
    for name, value in variables.items():
        command.extend(["-F", f"{name}={value}"])
    last_error = ""
    for attempt in range(5):
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode == 0:
            payload = json.loads(completed.stdout)
            if payload.get("errors"):
                raise RuntimeError(json.dumps(payload["errors"], sort_keys=True))
            return payload["data"]
        last_error = completed.stderr.decode(errors="replace").strip()
        if attempt < 4:
            time.sleep(2**attempt)
    raise RuntimeError(f"GitHub GraphQL failed after 5 attempts: {last_error}")


def pull_diff(repository: str, number: int) -> str:
    completed = subprocess.run(
        [
            "/usr/bin/curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--retry",
            "5",
            "--retry-all-errors",
            "--connect-timeout",
            "20",
            f"https://github.com/{repository}/pull/{number}.diff",
        ],
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("utf-8", errors="replace")


def patches_by_path(diff: str) -> dict[str, str]:
    result: dict[str, str] = {}
    current: list[str] = []
    old_path: str | None = None
    new_path: str | None = None

    def flush() -> None:
        if not current:
            return
        path = new_path if new_path and new_path != "/dev/null" else old_path
        if path and path != "/dev/null":
            result[path.removeprefix("a/").removeprefix("b/")] = "\n".join(current)

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            flush()
            current = [line]
            old_path = None
            new_path = None
            continue
        if not current:
            continue
        current.append(line)
        if line.startswith("--- "):
            old_path = line[4:].split("\t", 1)[0]
        elif line.startswith("+++ "):
            new_path = line[4:].split("\t", 1)[0]
    flush()
    return result


PULL_QUERY = """
query($owner:String!, $name:String!, $number:Int!, $after:String) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      body baseRefOid headRefOid mergedAt changedFiles
      mergeCommit { oid parents(first:1) { nodes { oid } } }
      files(first:100, after:$after) {
        nodes { path changeType additions deletions }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


def collect_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    owner, name = candidate["repository"].split("/", 1)
    variables: dict[str, object] = {
        "owner": owner,
        "name": name,
        "number": candidate["pull_request"],
        "after": "",
    }
    nodes: list[dict[str, Any]] = []
    pull: dict[str, Any] | None = None
    while True:
        data = graphql(PULL_QUERY, variables)
        repository = data.get("repository")
        pull = repository.get("pullRequest") if repository else None
        if pull is None or pull.get("mergeCommit") is None:
            raise RuntimeError("pull request or merge commit is unavailable")
        files = pull["files"]
        nodes.extend(files["nodes"])
        if not files["pageInfo"]["hasNextPage"]:
            break
        variables["after"] = files["pageInfo"]["endCursor"]
    assert pull is not None
    parents = pull["mergeCommit"]["parents"]["nodes"]
    if not parents:
        raise RuntimeError("merge commit has no parent")
    patches = patches_by_path(pull_diff(candidate["repository"], candidate["pull_request"]))
    status = {
        "ADDED": "added",
        "CHANGED": "modified",
        "COPIED": "copied",
        "DELETED": "removed",
        "MODIFIED": "modified",
        "RENAMED": "renamed",
    }
    return {
        **candidate,
        "body": pull.get("body") or "",
        "base_sha_at_open": pull["baseRefOid"],
        "head_sha": pull["headRefOid"],
        "merge_commit_sha": pull["mergeCommit"]["oid"],
        "merge_parent_sha": parents[0]["oid"],
        "merged_at": pull["mergedAt"],
        "changed_files": pull["changedFiles"],
        "files_returned": len(nodes),
        "files": [
            {
                "filename": item["path"],
                "previous_filename": None,
                "status": status.get(item["changeType"], item["changeType"].lower()),
                "additions": item["additions"],
                "deletions": item["deletions"],
                "changes": item["additions"] + item["deletions"],
                "patch": patches.get(item["path"]),
            }
            for item in nodes
        ],
    }


def main() -> int:
    spec = importlib.util.spec_from_file_location("reprocheck_v5_collect_graphql", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checkpoint = ROOT / "details.partial.json"
    output = ROOT / "details.json"
    if output.exists():
        raise FileExistsError(output)
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    details = json.loads(checkpoint.read_text(encoding="utf-8"))["details"]
    details = [
        item
        for item in details
        if "rate limit exceeded" not in str(item.get("collection_error", "")).lower()
    ]
    completed = {(item["repository"], item["pull_request"]) for item in details}
    pending = [
        item
        for item in sample["samples"]
        if (item["repository"], item["pull_request"]) not in completed
    ]
    for candidate in pending:
        detail = collect_candidate(candidate)
        details.append(detail)
        module._write_checkpoint(checkpoint, details)
        print(f"collected {len(details)}/{sample['sample_size']}", flush=True)
    module._write_checkpoint(output, details)
    checkpoint.unlink(missing_ok=True)
    print(json.dumps({"sample_size": len(details), "transport": "graphql+immutable-diff"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
