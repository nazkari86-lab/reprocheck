from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evidence_name(case_id: str, path: str) -> str:
    return f"{case_id}--{path.replace('/', '__')}"


def main() -> int:
    plan = json.loads((ROOT / "raw_evidence_plan.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    by_rank = {item["sample_rank"]: item for item in details}
    destination = ROOT / "raw_evidence"
    lock_path = ROOT / "raw_evidence.lock.json"
    if destination.exists() or lock_path.exists():
        raise FileExistsError("v4 raw-evidence snapshots already exist")
    destination.mkdir()
    lock: dict[str, Any] = {
        "schema_version": "reprocheck.upstream-discovery-raw-evidence-lock.v1",
        "files": {},
    }
    for case in plan["cases"]:
        item = by_rank[case["rank"]]
        commit = item["merge_commit_sha"]
        for path in case["files"]:
            url = f"https://raw.githubusercontent.com/{item['repository']}/{commit}/{path}"
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
                    url,
                ],
                check=True,
                capture_output=True,
            )
            data = completed.stdout
            filename = evidence_name(case["case_id"], path)
            (destination / filename).write_bytes(data)
            lock["files"][filename] = {
                "case_id": case["case_id"],
                "repository": item["repository"],
                "commit": commit,
                "path": path,
                "sha256": sha256(data),
                "url": url,
            }
    lock_path.write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: fetched {len(lock['files'])} immutable raw-evidence artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
