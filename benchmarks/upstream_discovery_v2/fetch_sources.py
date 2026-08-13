from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    sources = ROOT / "sources"
    sources.mkdir(exist_ok=True)
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
                    ["/usr/bin/curl", "--fail", "--location", "--silent", "--show-error", url],
                    check=True,
                    capture_output=True,
                )
                data = completed.stdout
                suffix = Path(path).suffix or ".txt"
                filename = f"{case['id']}--{path.replace('/', '__')}.{phase}{suffix}"
                destination = sources / filename
                destination.write_bytes(data)
                lock["files"][filename] = {"sha256": _sha256(data), "url": url}
    (ROOT / "sources.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: fetched {len(lock['files'])} prospective immutable files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
