from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_name(case_id: str, path: str, phase: str) -> str:
    suffix = Path(path).suffix or ".txt"
    return f"{case_id}--{path.replace('/', '__')}.{phase}{suffix}"


def main() -> int:
    plan = json.loads((ROOT / "source_plan.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    by_rank = {item["sample_rank"]: item for item in details}
    destination = ROOT / "sources"
    destination.mkdir(exist_ok=True)
    lock_path = ROOT / "sources.lock.json"
    if lock_path.exists():
        lock: dict[str, object] = json.loads(lock_path.read_text(encoding="utf-8"))
    else:
        lock = {
            "schema_version": "reprocheck.upstream-discovery-sources-lock.v5",
            "files": {},
        }
    for case in plan["cases"]:
        item = by_rank[case["rank"]]
        for path in case["files"]:
            for phase, commit in (
                ("before", item["merge_parent_sha"]),
                ("after", item["merge_commit_sha"]),
            ):
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
                filename = source_name(case["id"], path, phase)
                if filename in lock["files"]:
                    existing = destination / filename
                    if sha256(existing.read_bytes()) != lock["files"][filename]["sha256"]:
                        raise RuntimeError(f"locked source changed locally: {filename}")
                    continue
                (destination / filename).write_bytes(data)
                lock["files"][filename] = {"sha256": sha256(data), "url": url}
    (ROOT / "sources.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: fetched {len(lock['files'])} immutable v5 source snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
