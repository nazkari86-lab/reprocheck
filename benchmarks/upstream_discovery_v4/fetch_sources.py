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
    if destination.exists() or (ROOT / "sources.lock.json").exists():
        raise FileExistsError("v4 source snapshots already exist")
    destination.mkdir()
    lock: dict[str, object] = {
        "schema_version": "reprocheck.upstream-discovery-sources-lock.v2",
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
                (destination / filename).write_bytes(data)
                lock["files"][filename] = {"sha256": sha256(data), "url": url}
    (ROOT / "sources.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: fetched {len(lock['files'])} immutable v4 source snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
