from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import urllib.parse

from acquire import GitHubREST
from reprocheck.ml_materialization import (
    load_materialization_rules,
    materialize_discovery,
    verify_materialization,
)


class GitHubContents(GitHubREST):
    @staticmethod
    def _repository(full_name: str) -> str:
        return "/".join(urllib.parse.quote(part, safe="") for part in full_name.split("/"))

    def tree(self, full_name: str, commit_sha: str):  # type: ignore[no-untyped-def]
        payload = self._get(
            f"repos/{self._repository(full_name)}/git/trees/{commit_sha}", {"recursive": "1"}
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("tree"), list):
            raise ValueError(f"GitHub tree lookup returned an invalid payload for {full_name}")
        return {
            "truncated": payload.get("truncated"),
            "entries": [
                {
                    "path": item.get("path"),
                    "type": item.get("type"),
                    "sha": item.get("sha"),
                    "size": item.get("size", 0),
                }
                for item in payload["tree"]
            ],
        }

    def blob(self, full_name: str, blob_sha: str) -> bytes:
        payload = self._get(f"repos/{self._repository(full_name)}/git/blobs/{blob_sha}")
        if (
            not isinstance(payload, dict)
            or payload.get("encoding") != "base64"
            or not isinstance(payload.get("content"), str)
        ):
            raise ValueError(f"GitHub blob lookup returned an invalid payload for {full_name}")
        try:
            compact_content = "".join(payload["content"].split())
            return base64.b64decode(compact_content, validate=True)
        except ValueError as error:
            raise ValueError(f"GitHub blob contains invalid base64 for {full_name}") from error


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command", required=True)
run = subparsers.add_parser("run")
run.add_argument("--discovery", type=Path, required=True)
run.add_argument("--rules", type=Path, required=True)
run.add_argument("--output-dir", type=Path, required=True)
verify = subparsers.add_parser("verify")
verify.add_argument("--rules", type=Path, required=True)
verify.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
rules = load_materialization_rules(args.rules)
if args.command == "run":
    discovery = json.loads(args.discovery.read_text(encoding="utf-8"))
    result = materialize_discovery(
        discovery, rules, GitHubContents(os.environ.get("GITHUB_TOKEN")), args.output_dir
    )
    print(
        f"included={result['included_repository_count']} artifacts={result['artifact_count']} "
        f"bytes={result['total_bytes']} sha256={result['materialization_sha256']}"
    )
else:
    errors = verify_materialization(args.output_dir, rules)
    for error in errors:
        print(f"FAIL: {error}")
    raise SystemExit(1 if errors else 0)
