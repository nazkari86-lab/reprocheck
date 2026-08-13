from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if (ROOT / "study.lock.json").exists():
        raise FileExistsError("v10 study is already frozen")
    labels = json.loads((ROOT / "labels.json").read_text())
    sample = json.loads((ROOT / "sample.json").read_text())
    selected_ranks = {label["rank"] for label in labels["labels"] if label["eligible"] is True}
    source_locks = []
    for item in sample["samples"]:
        if item["sample_rank"] not in selected_ranks:
            continue
        path = ROOT / item["source_file"]
        source_locks.append({
            "rank": item["sample_rank"],
            "repository": item["repository"],
            "blob_sha": item["blob_sha"],
            "file": item["source_file"],
            "sha256": digest(path),
        })
    lock = {
        "schema_version": "reprocheck.cross-project-study-lock.v10",
        "extractor_commit": "734a3d5b4ec421bcccacede69df4f86f7c1900fe",
        "extractor_version": "0.24.0",
        "eligible_documents": labels["eligible_documents"],
        "selected_claims": labels["selected_claims"],
        "sha256": {
            "registration.json": digest(ROOT / "registration.json"),
            "protocol.md": digest(ROOT / "protocol.md"),
            "frames.json": digest(ROOT / "frames.json"),
            "sample.json": digest(ROOT / "sample.json"),
            "labels.json": digest(ROOT / "labels.json"),
            "finalize_labels.py": digest(ROOT / "finalize_labels.py"),
            "../../src/reprocheck/claims.py": digest(ROOT.parent.parent / "src/reprocheck/claims.py"),
            "../../src/reprocheck/metric_names.py": digest(ROOT.parent.parent / "src/reprocheck/metric_names.py"),
        },
        "sources": source_locks,
    }
    (ROOT / "study.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"sources": len(source_locks), "claims": labels["selected_claims"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
