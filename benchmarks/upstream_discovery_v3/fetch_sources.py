from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    destination = ROOT / "sources"
    destination.mkdir(exist_ok=True)
    lock: dict[str, object] = {
        "schema_version": "reprocheck.upstream-discovery-sources-lock.v1",
        "files": {},
    }
    for case in manifest["cases"]:
        for path in case["files"]:
            for phase, commit in (
                ("before", case["parent_commit"]),
                ("after", case["merge_commit"]),
            ):
                url = f"https://raw.githubusercontent.com/{case['repository']}/{commit}/{path}"
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
                suffix = Path(path).suffix or ".txt"
                filename = f"{case['id']}--{path.replace('/', '__')}.{phase}{suffix}"
                (destination / filename).write_bytes(data)
                lock["files"][filename] = {"sha256": sha256(data), "url": url}
    (ROOT / "sources.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: fetched {len(lock['files'])} source snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
