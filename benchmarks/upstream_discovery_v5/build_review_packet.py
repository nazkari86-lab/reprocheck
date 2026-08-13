from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
NUMBER = re.compile(r"(?<![A-Za-z_])[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)%?(?![A-Za-z_])")
REPORT_SUFFIXES = {".csv", ".html", ".json", ".md", ".rst", ".tex", ".tsv", ".txt", ".yaml", ".yml"}


def _numeric_diff_lines(patch: str | None) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    added: list[str] = []
    if not patch:
        return removed, added
    for line in patch.splitlines():
        if line.startswith("-") and not line.startswith("---") and NUMBER.search(line[1:]):
            removed.append(line)
        elif line.startswith("+") and not line.startswith("+++") and NUMBER.search(line[1:]):
            added.append(line)
    return removed, added


def build() -> dict[str, int]:
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    reviews = []
    for item in details:
        paired = []
        missing_report_patches = []
        for file in item["files"]:
            suffix = Path(file["filename"]).suffix.lower()
            if suffix not in REPORT_SUFFIXES:
                continue
            if file.get("patch") is None:
                missing_report_patches.append(file["filename"])
                continue
            removed, added = _numeric_diff_lines(file["patch"])
            if removed and added:
                paired.append(
                    {
                        "filename": file["filename"],
                        "status": file["status"],
                        "removed_numeric_lines": removed,
                        "added_numeric_lines": added,
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
                "paired_numeric_report_files": paired,
                "report_files_without_patch": missing_report_patches,
            }
        )
    payload = {
        "schema_version": "reprocheck.upstream-discovery-review-packet.v5",
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
        "with_paired_numeric_report_change": sum(
            bool(review["paired_numeric_report_files"]) for review in reviews
        ),
        "with_missing_report_patch": sum(
            bool(review["report_files_without_patch"]) for review in reviews
        ),
    }


if __name__ == "__main__":
    print(json.dumps(build(), sort_keys=True))
