from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT_NAME = "reprocheck-evidence-trial-v19-curator"
FIXED_TIME = (2024, 1, 1, 0, 0, 0)
PRIVATE_FIELDS = {
    "gold_status",
    "gold_metric",
    "gold_value",
    "gold_rationale",
    "gold_evidence_refs",
    "prediction",
    "predictions",
    "evaluator_output",
    "evaluator_outputs",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _descriptor(name: str, data: bytes) -> dict[str, Any]:
    return {"filename": name, "sha256": _sha256(data), "size_bytes": len(data)}


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _contains_private_field(value: object) -> bool:
    if isinstance(value, dict):
        return bool(PRIVATE_FIELDS.intersection(value)) or any(
            _contains_private_field(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_private_field(item) for item in value)
    return False


def _load_payloads(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    packet_path = root / "curation-packet.json"
    packet_bytes = packet_path.read_bytes()
    packet = json.loads(packet_bytes)
    if (
        not isinstance(packet, dict)
        or packet.get("schema_version") != "reprocheck.evidence-trial-curation-packet.v1"
        or packet.get("blind_to_outcome_labels") is not True
        or _contains_private_field(packet)
    ):
        raise ValueError("curation packet is missing or not structurally outcome-blind")
    candidates = packet.get("candidates")
    if not isinstance(candidates, list) or packet.get("candidate_count") != len(candidates):
        raise ValueError("curation packet candidate count does not match")
    payloads = {
        "curation_app.py": (root / "curation_app.py").read_bytes(),
        "curation-packet.json": packet_bytes,
        "CURATOR_GUIDE.md": (root / "CURATOR_GUIDE.md").read_bytes(),
    }
    seen_sources: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("source_file"), str):
            raise ValueError("curation packet contains an invalid candidate")
        relative = candidate["source_file"]
        if relative in seen_sources or not relative.startswith("sources/"):
            raise ValueError("curation packet source paths must be unique and confined")
        seen_sources.add(relative)
        path = (root / "acquisition-v5" / relative).resolve()
        source_root = (root / "acquisition-v5" / "sources").resolve()
        if not path.is_relative_to(source_root) or not path.is_file():
            raise ValueError(f"curation source is unavailable: {relative}")
        data = path.read_bytes()
        if _sha256(data) != candidate.get("source_sha256") or len(data) != candidate.get(
            "source_bytes"
        ):
            raise ValueError(f"curation source checksum mismatch: {relative}")
        data.decode("utf-8")
        payloads[f"acquisition-v5/{relative}"] = data
    if len(seen_sources) != len(candidates):
        raise ValueError("curation packet does not map one source per candidate")
    return payloads, packet


def build(root: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("curator handoff output already exists")
    payloads, packet = _load_payloads(root)
    payloads["START_HERE.md"] = b"""# Start here

This is the outcome-blind ReproCheck Evidence Trial v19 curator handoff.

Requirements: Python 3.11 or newer and a local web browser. No package install,
network access, evaluator output, gold label, or ReproCheck checkout is required.

Run from this extracted directory:

```bash
python3 curation_app.py
```

Open the printed loopback URL. Inspect all candidate files, export both JSON files,
and return them unchanged to the study operator. Do not add or infer outcome labels.
See `CURATOR_GUIDE.md` for the complete source-only protocol.
"""
    entries = [_descriptor(name, payloads[name]) for name in sorted(payloads)]
    manifest = {
        "schema_version": "reprocheck.evidence-trial-curator-handoff.v1",
        "role": "independent_source_only_curator",
        "candidate_count": packet["candidate_count"],
        "curation_packet_sha256": _sha256(payloads["curation-packet.json"]),
        "entry_count": len(entries),
        "entries": entries,
        "contains_gold_labels": False,
        "contains_evaluator_outputs": False,
        "contains_reviewer_outputs": False,
        "server_persists_labels": False,
        "network_required": False,
    }
    payloads["HANDOFF.json"] = _json_bytes(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(f"{ROOT_NAME}/{name}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(
                info, payloads[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
    zip_bytes = output.read_bytes()
    return {
        "schema_version": "reprocheck.evidence-trial-curator-handoff-build.v1",
        "filename": output.name,
        "sha256": _sha256(zip_bytes),
        "size_bytes": len(zip_bytes),
        "candidate_count": packet["candidate_count"],
        "payload_entry_count": len(payloads),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic v19 curator handoff")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/evidence-trial-v19-curator.zip"),
    )
    args = parser.parse_args(argv)
    try:
        result = build(args.root.resolve(), args.output.resolve())
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
