from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
NUMBER = re.compile(r"(?<![A-Za-z_])[+-]?(?:\d+(?:\.\d+)?|\.\d+)%?(?![A-Za-z_])")


def _numeric_diff_lines(patch: str | None) -> list[str]:
    if not patch:
        return []
    lines = []
    for line in patch.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        if NUMBER.search(line[1:]):
            lines.append(line)
    return lines


def build() -> dict[str, object]:
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    reviews = []
    for item in details:
        changed = []
        for file in item["files"]:
            numeric_lines = _numeric_diff_lines(file.get("patch"))
            if numeric_lines:
                changed.append(
                    {
                        "filename": file["filename"],
                        "status": file["status"],
                        "numeric_diff_lines": numeric_lines,
                    }
                )
        reviews.append(
            {
                "rank": item["sample_rank"],
                "repository": item["repository"],
                "pull_request": item["pull_request"],
                "url": item["url"],
                "title": item["title"],
                "body": item["body"],
                "merge_parent_sha": item["merge_parent_sha"],
                "merge_commit_sha": item["merge_commit_sha"],
                "changed_files": item["changed_files"],
                "files_with_numeric_changes": changed,
            }
        )
    payload = {
        "schema_version": "reprocheck.upstream-discovery-review-packet.v1",
        "parser_output_used": False,
        "sample_size": len(reviews),
        "reviews": reviews,
    }
    (ROOT / "review_packet.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "sample_size": len(reviews),
        "with_numeric_diff_lines": sum(
            bool(review["files_with_numeric_changes"]) for review in reviews
        ),
    }


def main() -> int:
    print(json.dumps(build(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
