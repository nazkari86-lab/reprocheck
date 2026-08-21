from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from reprocheck.ml_acquisition import (
    discover_repositories,
    load_source_frame,
    verify_discovery,
    write_discovery,
)
from reprocheck.ml_dataset import load_ml_dataset


class GitHubREST:
    def __init__(self, token: str | None) -> None:
        self.token = token

    def _get(self, endpoint: str, parameters: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
        suffix = "?" + urllib.parse.urlencode(parameters) if parameters else ""
        request = urllib.request.Request(
            f"https://api.github.com/{endpoint}{suffix}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ReproCheck-ML-acquisition/1",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            raise ValueError(f"GitHub API request failed for {endpoint}: {error}") from error

    def search(self, query: str, *, limit: int) -> list[dict[str, object]]:
        payload = self._get(
            "search/repositories",
            {"q": query, "sort": "stars", "order": "desc", "per_page": str(limit)},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("GitHub repository search returned an invalid payload")
        results = []
        for item in payload["items"]:
            owner = item.get("owner") or {}
            license_record = item.get("license") or {}
            results.append(
                {
                    "full_name": item.get("full_name"),
                    "html_url": item.get("html_url"),
                    "owner_id": owner.get("id"),
                    "owner_login": owner.get("login"),
                    "fork": item.get("fork"),
                    "archived": item.get("archived"),
                    "license": license_record.get("spdx_id"),
                    "default_branch": item.get("default_branch"),
                    "stargazers_count": item.get("stargazers_count"),
                }
            )
        return results

    def resolve_head(self, full_name: str, default_branch: str) -> str:
        repository = "/".join(urllib.parse.quote(part, safe="") for part in full_name.split("/"))
        branch = urllib.parse.quote(default_branch, safe="")
        payload = self._get(f"repos/{repository}/commits/{branch}")
        if not isinstance(payload, dict) or not isinstance(payload.get("sha"), str):
            raise ValueError(f"GitHub commit lookup returned an invalid payload for {full_name}")
        return payload["sha"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen ReproCheck-ML corpus acquisition")
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover = subparsers.add_parser("discover")
    discover.add_argument(
        "--source-frame", type=Path, default=Path(__file__).with_name("source-frame.json")
    )
    discover.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify-discovery")
    verify.add_argument("--discovery", type=Path, required=True)
    validate = subparsers.add_parser("validate-corpus")
    validate.add_argument("--corpus", type=Path, required=True)
    validate.add_argument("--annotations", type=Path, required=True)
    validate.add_argument("--sources-root", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "discover":
        frame = load_source_frame(args.source_frame)
        result = discover_repositories(frame, GitHubREST(os.environ.get("GITHUB_TOKEN")))
        write_discovery(result, args.output)
        print(
            f"status={result['status']} owners={result['selected_owner_count']} "
            f"sha256={result['discovery_sha256']} output={args.output.resolve()}"
        )
        return 0 if result["status"] == "target_reached" else 1
    if args.command == "verify-discovery":
        try:
            payload = json.loads(args.discovery.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            print(f"FAIL: cannot load discovery: {error}")
            return 2
        errors = verify_discovery(payload)
        for error in errors:
            print(f"FAIL: {error}")
        return 1 if errors else 0
    dataset = load_ml_dataset(args.corpus, args.annotations, sources_root=args.sources_root)
    print(
        f"PASS: repositories={dataset.repository_count} blocks={dataset.block_count} "
        f"claims={dataset.claim_count} dataset_sha256={dataset.dataset_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
