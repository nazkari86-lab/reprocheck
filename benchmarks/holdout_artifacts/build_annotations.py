from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
PREREGISTRATION_LOCK = ROOT / "preregistration.lock.json"
OUTPUT = ROOT / "annotations.json"
_NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?")


class _HTMLTables(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._depth = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "table":
            if self._depth == 0:
                self._rows = []
            self._depth += 1
        elif self._depth and tag == "tr":
            self._flush_row()
            self._row = []
        elif self._depth and tag in {"th", "td"}:
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
        elif tag == "tr":
            self._flush_row()
        elif tag == "table" and self._depth:
            self._flush_row()
            self._depth -= 1
            if self._depth == 0 and self._rows:
                self.tables.append(self._rows)
                self._rows = []

    def _flush_row(self) -> None:
        if self._row:
            self._rows.append(self._row)
        self._row = None


def _plain(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _markdown_row(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    escaped_pipe = "\x00HOLDOUT_PIPE\x00"
    stripped = line.strip().replace(r"\|", escaped_pipe).strip("|")
    cells = [_plain(cell.replace(escaped_pipe, "|")) for cell in stripped.split("|")]
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
    plain = _plain(header).casefold().replace("–", "-").replace("—", "-")
    normalized = re.sub(r"[^a-z0-9@.:-]+", " ", plain).strip()
    if not re.search(r"\b(?:m?ap)(?=$|[^a-z])|\baverage\s+precision\b", normalized):
        return None
    if re.search(r"\b(?:m?ap)[scrfml]\b", normalized) or re.search(
        r"\b(?:s|m|l|small|medium|large)$", normalized
    ):
        return None
    if re.search(r"(?:m?ap).*?(?:50\s*[-:]\s*95|0?\.5(?:0)?\s*[-:]\s*0?\.95)", normalized):
        return "ap"
    if re.search(r"(?:m?ap).*?(?:\b75\b|\b0?\.75\b)", normalized):
        return "ap75"
    if re.search(r"(?:m?ap).*?(?:\b50\b|\b0?\.5(?:0)?\b)", normalized):
        return "ap50"
    return "ap"


def _numeric_cell(cell: str) -> float | None:
    matches = _NUMBER_RE.findall(_plain(cell))
    if len(matches) != 1:
        return None
    value = float(matches[0].replace(",", "."))
    if not math.isfinite(value) or not 0 <= value <= 100:
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
                        "review": "preregistered_independent_table_rule",
                    }
                )
    return claims


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lock = json.loads(PREREGISTRATION_LOCK.read_text(encoding="utf-8"))
    if manifest.get("preregistration_sha256") != lock["preregistration_sha256"]:
        raise ValueError("manifest is not bound to the locked preregistration")
    if manifest.get("evaluator_sha256") != lock["evaluator_sha256"]:
        raise ValueError("manifest is not bound to the frozen evaluator")
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
                "source_sha256": _sha256(source),
                "expected_claims": _table_claims(text),
                "annotation_method": "preregistered_independent_ap_table_rule",
            }
        )
    return {
        "schema": "reprocheck.preregistered-holdout-annotations.v1",
        "preregistration_sha256": lock["preregistration_sha256"],
        "evaluator_sha256": lock["evaluator_sha256"],
        "scope": (
            "unambiguous numeric cells under AP, mAP, AP50, or AP75 Markdown or HTML table headers"
        ),
        "annotations_created_before_evaluator_run": True,
        "annotation_created_without_reprocheck_imports_or_outputs": True,
        "reviewers": {
            "rule_derived": True,
            "internal_human": 1,
            "independent_external": 0,
            "adjudication": False,
        },
        "pre_output_review": (
            "All unique metric headers and per-artifact claim samples were inspected "
            "before any evaluator output was generated."
        ),
        "limitations": [
            "Only the preregistered AP-family table-cell scope is labelled.",
            "Narrative claims, size-specific AP variants, and multi-number cells are excluded.",
            "Labels are generated by an internal rule, not independent expert review.",
        ],
        "artifacts": sorted(artifacts, key=lambda item: item["local_path"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build or verify preregistered holdout labels")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build()
    except (KeyError, OSError, UnicodeDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(serialized, encoding="utf-8")
        action = "wrote"
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != serialized:
        print("ERROR: holdout annotations differ; review and run with --write")
        return 1
    else:
        action = "verified"
    claims = sum(len(item["expected_claims"]) for item in result["artifacts"])
    claim_bearing = sum(bool(item["expected_claims"]) for item in result["artifacts"])
    print(
        f"{action} artifacts={len(result['artifacts'])} "
        f"claim_bearing={claim_bearing} claims={claims}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
