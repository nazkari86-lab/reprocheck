from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    sources = ROOT / "sources"
    sources.mkdir(exist_ok=True)
    lock: dict[str, object] = {
        "schema_version": "reprocheck.upstream-corrections-lock.v1",
        "files": {},
    }
    for correction in manifest["corrections"]:
        repo = correction["repository"]
        path = correction["path"]
        for phase, commit in (
            ("before", correction["parent_commit"]),
            ("after", correction["merge_commit"]),
        ):
            url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
            completed = subprocess.run(
                ["/usr/bin/curl", "--fail", "--location", "--silent", "--show-error", url],
                check=True,
                capture_output=True,
            )
            data = completed.stdout
            destination = sources / f"{correction['id']}.{phase}{Path(path).suffix}"
            destination.write_bytes(data)
            lock["files"][destination.name] = {"sha256": _sha256(data), "url": url}
        evidence = correction.get("raw_evidence")
        if evidence:
            url = evidence["url"]
            completed = subprocess.run(
                ["/usr/bin/curl", "--fail", "--location", "--silent", "--show-error", url],
                check=True,
                capture_output=True,
            )
            evidence_suffix = evidence.get("suffix", ".jsonl")
            destination = sources / f"{correction['id']}.evidence{evidence_suffix}"
            destination.write_bytes(completed.stdout)
            lock["files"][destination.name] = {
                "sha256": _sha256(completed.stdout),
                "url": url,
            }
    (ROOT / "sources.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: fetched {len(lock['files'])} immutable upstream files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
