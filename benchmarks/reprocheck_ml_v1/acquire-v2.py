from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from acquire import GitHubREST
from reprocheck.ml_acquisition import _load_object
from reprocheck.ml_acquisition_v2 import discover_balanced_repositories, verify_balanced_discovery


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command", required=True)
discover = subparsers.add_parser("discover")
discover.add_argument(
    "--source-frame", type=Path, default=Path(__file__).with_name("source-frame-v2.json")
)
discover.add_argument("--output", type=Path, required=True)
verify = subparsers.add_parser("verify")
verify.add_argument("--discovery", type=Path, required=True)
args = parser.parse_args()

if args.command == "discover":
    frame = _load_object(args.source_frame, "v2 source frame")
    result = discover_balanced_repositories(frame, GitHubREST(os.environ.get("GITHUB_TOKEN")))
    errors = verify_balanced_discovery(result)
    if errors:
        raise ValueError("; ".join(errors))
    if args.output.exists():
        raise ValueError(f"discovery output already exists: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"status={result['status']} owners={result['selected_owner_count']} sha256={result['discovery_sha256']}"
    )
    raise SystemExit(0 if result["status"] == "target_reached" else 1)

payload = json.loads(args.discovery.read_text(encoding="utf-8"))
errors = verify_balanced_discovery(payload)
for error in errors:
    print(f"FAIL: {error}")
raise SystemExit(1 if errors else 0)
