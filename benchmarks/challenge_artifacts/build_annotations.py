from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
OUTPUT = ROOT / "annotations.json"
_NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)")


class _HTMLTables(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "table":
            if self._table_depth == 0:
                self._rows = []
            self._table_depth += 1
        elif self._table_depth and tag == "tr":
            if self._row:
                self._rows.append(self._row)
            self._row = []
        elif self._table_depth and tag in {"th", "td"}:
            if tag == "th" and self._row is None:
                self._row = []
            self._cell = []
        elif self._cell is not None and tag == "br":
            self._cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell is not None:
            if self._row is not None:
                self._row.append(_plain("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            if self._row:
                self._rows.append(self._row)
                self._row = None
            self._table_depth -= 1
            if self._table_depth == 0 and self._rows:
                self.tables.append(self._rows)
                self._rows = []


def _plain(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _markdown_row(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    sentinel = "\x00PIPE\x00"
    stripped = line.strip().replace(r"\|", sentinel).strip("|")
    cells = [_plain(cell.replace(sentinel, "|")) for cell in stripped.split("|")]
    return cells if len(cells) >= 2 else None


def _markdown_tables(text: str) -> list[list[list[str]]]:
    lines = text.splitlines()
    tables: list[list[list[str]]] = []
    index = 0
    while index + 1 < len(lines):
        headers = _markdown_row(lines[index])
        separators = _markdown_row(lines[index + 1])
        if (
            not headers
            or not separators
            or not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separators)
        ):
            index += 1
            continue
        rows = [headers]
        row_index = index + 2
        while row_index < len(lines):
            row = _markdown_row(lines[row_index])
            if not row:
                break
            rows.append(row)
            row_index += 1
        tables.append(rows)
        index = max(row_index, index + 1)
    return tables


def _html_tables(text: str) -> list[list[list[str]]]:
    parser = _HTMLTables()
    parser.feed(text)
    parser.close()
    return parser.tables


def _metric_header(header: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", _plain(header).casefold()).strip()
    compact = normalized.replace(" ", "")
    words = normalized.split()
    prefix = None
    if any(token in words or token in compact for token in ("bbox", "box")):
        prefix = "box"
    elif any(token in words or token in compact for token in ("segm", "mask")):
        prefix = "mask"
    elif "proposal" in compact or "prop" in words:
        prefix = "proposal"
    elif "keypoint" in compact or "keypoints" in compact or "kp" in words:
        prefix = "keypoint"

    family = None
    if re.search(r"(?:^|[^a-z])(?:m?ap)\s*50(?:[^0-9]|$)", normalized):
        family = "ap50"
    elif re.search(r"(?:^|[^a-z])(?:m?ap)\s*75(?:[^0-9]|$)", normalized):
        family = "ap75"
    elif re.search(r"(?:^|[^a-z])m?ap(?:[^a-z]|$)", normalized):
        family = "ap"
    elif re.search(r"(?:^|[^a-z])ar(?:[^a-z]|$)", normalized):
        family = "ar"
    elif re.search(r"(?:^|[^a-z])pq(?:[^a-z]|$)", normalized):
        family = "pq"
    if family is None:
        return None
    return f"{prefix}_{family}" if prefix else family


def _numeric_cell(cell: str) -> float | None:
    plain = _plain(cell)
    matches = _NUMBER_RE.findall(plain)
    if len(matches) != 1:
        return None
    value = float(matches[0].replace(",", "."))
    if not 0 <= value <= 100:
        return None
    return value / 100 if value > 1 else value


def _table_claims(text: str) -> list[dict[str, Any]]:
    tables = [*_markdown_tables(text), *_html_tables(text)]
    claims: list[dict[str, Any]] = []
    for table_index, table in enumerate(tables):
        if len(table) < 2:
            continue
        headers = table[0]
        metrics = [_metric_header(header) for header in headers]
        for row_index, row in enumerate(table[1:], start=1):
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(row):
                    continue
                value = _numeric_cell(row[column])
                if value is None:
                    continue
                claims.append(
                    {
                        "metric": metric,
                        "value": value,
                        "origin": (
                            f"table={table_index};row={row_index};column={column};"
                            f"header={headers[column]}"
                        ),
                        "row_label": row[0] if row else "",
                        "review": "rule_derived_challenge_table",
                    }
                )
    return claims


def build() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifacts = []
    for entry in manifest["entries"]:
        if entry["kind"] != "artifact":
            continue
        source = SOURCES / entry["local_path"]
        text = source.read_text(encoding="utf-8")
        artifacts.append(
            {
                "repository": entry["repository"],
                "local_path": entry["local_path"],
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "expected_claims": _table_claims(text),
                "annotation_method": "independent_ap_ar_pq_table_rule",
            }
        )
    return {
        "schema": "reprocheck.challenge-artifact-annotations.v1",
        "scope": "numeric cells under AP, AP50, AP75, AR, or PQ table headers only",
        "selection_frozen_before_zero_shot_evaluation": True,
        "annotation_created_without_reprocheck_outputs": True,
        "reviewers": {
            "rule_derived": True,
            "independent_external_reviewers": 0,
            "adjudication": False,
        },
        "limitations": [
            "Only declared AP, AR, and PQ table cells are labelled.",
            "Narrative claims and other metric families are outside annotation scope.",
            "Labels are generated by an internal rule, not independent expert review.",
        ],
        "artifacts": sorted(artifacts, key=lambda item: item["local_path"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build or verify challenge annotations")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = build()
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(serialized, encoding="utf-8")
        action = "wrote"
    else:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != serialized:
            print("ERROR: challenge annotations differ; review and run with --write")
            return 1
        action = "verified"
    claim_count = sum(len(item["expected_claims"]) for item in result["artifacts"])
    bearing = sum(bool(item["expected_claims"]) for item in result["artifacts"])
    print(
        f"{action} artifacts={len(result['artifacts'])} "
        f"claim_bearing={bearing} claims={claim_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
