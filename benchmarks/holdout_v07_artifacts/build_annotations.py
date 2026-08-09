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
LOCK = ROOT / "preregistration.lock.json"
OUTPUT = ROOT / "annotations.json"
NUMBER = re.compile(
    r"(?P<value>[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?)\s*(?P<percent>%)?"
)
UNIT_INTERVAL = {
    "accuracy",
    "top1_accuracy",
    "top5_accuracy",
    "precision",
    "recall",
    "f1",
    "dice",
    "iou",
    "miou",
    "ap",
    "ap50",
    "ap75",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!?(?:\[([^]]*)\])\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _split_row(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    marker = "\x00PIPE\x00"
    stripped = line.strip().replace(r"\|", marker).strip("|")
    cells = [cell.replace(marker, "|").strip() for cell in stripped.split("|")]
    return cells if len(cells) >= 2 else None


def _separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _metric(header: str) -> str | None:
    compact = re.sub(r"[^a-z0-9]+", " ", _plain(header).casefold()).strip()
    words = compact.split()
    if not words:
        return None
    if re.search(r"\b(?:ap|average precision)\b", compact) and (
        set(words) & {"small", "medium", "large"} or words[-1] in {"s", "m", "l"}
    ):
        return None
    candidates: list[str] = []
    if re.search(r"\btop\s*1\b|\btop1\b", compact):
        candidates.append("top1_accuracy")
    if re.search(r"\btop\s*5\b|\btop5\b", compact):
        candidates.append("top5_accuracy")
    if re.search(r"\baccuracy\b|\bacc\b", compact) and not candidates:
        candidates.append("accuracy")
    if re.search(r"\bmiou\b|\bmean\s+iou\b", compact):
        candidates.append("miou")
    elif re.search(r"\biou\b|intersection over union", compact):
        candidates.append("iou")
    if re.search(r"\bdice\b", compact):
        candidates.append("dice")
    is_ap = bool(re.search(r"\bap(?:\s*\d+)?\b|\bmap(?:\s*\d+)?\b|average precision", compact))
    if is_ap:
        if re.search(r"50\s+95", compact):
            candidates.append("ap")
        elif re.search(r"(?:ap|map)\s*75\b", compact):
            candidates.append("ap75")
        elif re.search(r"(?:ap|map)\s*50\b", compact):
            candidates.append("ap50")
        else:
            candidates.append("ap")
    if re.search(r"\bprecision\b", compact) and "average precision" not in compact:
        candidates.append("precision")
    if re.search(r"\brecall\b", compact) and "average recall" not in compact:
        candidates.append("recall")
    if re.search(r"\bf1\b", compact):
        candidates.append("f1")
    for token in ("bleu", "wer", "cer", "rmse", "mae"):
        if re.search(rf"\b{token}\b", compact):
            candidates.append(token)
    if re.search(r"\br\s*2\b|\br2\b", compact):
        candidates.append("r2")
    unique = list(dict.fromkeys(candidates))
    return unique[0] if len(unique) == 1 else None


def _value(metric: str, cell: str) -> float | None:
    matches = list(NUMBER.finditer(_plain(cell)))
    if len(matches) != 1:
        return None
    match = matches[0]
    value = float(match.group("value").replace(",", "."))
    if not math.isfinite(value):
        return None
    if match.group("percent") or (metric in UNIT_INTERVAL and 1 < value <= 100):
        value /= 100
    return value


def _markdown_claims(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    claims = []
    table_index = 0
    index = 0
    while index + 1 < len(lines):
        headers = _split_row(lines[index])
        separators = _split_row(lines[index + 1])
        if not headers or not separators or not _separator(separators):
            index += 1
            continue
        table_index += 1
        metrics = [_metric(header) for header in headers]
        row_index = index + 2
        row_number = 0
        while row_index < len(lines):
            cells = _split_row(lines[row_index])
            if not cells:
                break
            row_number += 1
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                value = _value(metric, cells[column])
                if value is None:
                    continue
                claims.append(
                    {
                        "metric": metric,
                        "value": value,
                        "origin": f"markdown_table={table_index};row={row_number};column={column};header={_plain(headers[column])}",
                        "row_label": _plain(cells[0]) if cells else "",
                        "review": "preregistered_independent_table_rule",
                    }
                )
            row_index += 1
        index = max(row_index, index + 1)
    return claims


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
            if not self._depth:
                self._rows = []
            self._depth += 1
        elif self._depth and tag == "tr":
            self._flush()
            self._row = []
        elif self._depth and tag in {"th", "td"}:
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
            self._flush()
        elif tag == "table" and self._depth:
            self._flush()
            self._depth -= 1
            if not self._depth and self._rows:
                self.tables.append(self._rows)

    def _flush(self) -> None:
        if self._row:
            self._rows.append(self._row)
        self._row = None


def _html_claims(text: str) -> list[dict[str, Any]]:
    parser = _HTMLTables()
    parser.feed(text)
    claims = []
    for table_index, table in enumerate(parser.tables, start=1):
        if len(table) < 2:
            continue
        headers = table[0]
        metrics = [_metric(header) for header in headers]
        for row_number, cells in enumerate(table[1:], start=1):
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                value = _value(metric, cells[column])
                if value is None:
                    continue
                claims.append(
                    {
                        "metric": metric,
                        "value": value,
                        "origin": f"html_table={table_index};row={row_number};column={column};header={headers[column]}",
                        "row_label": cells[0] if cells else "",
                        "review": "preregistered_independent_table_rule",
                    }
                )
    return claims


def build() -> dict[str, Any]:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if _sha256(ROOT / "preregistration.json") != lock["preregistration_sha256"]:
        raise ValueError("preregistration changed after lock")
    if manifest["preregistration_sha256"] != lock["preregistration_sha256"]:
        raise ValueError("source manifest preregistration binding mismatch")
    artifacts = []
    for entry in manifest["entries"]:
        if entry["kind"] != "artifact":
            continue
        path = SOURCES / entry["local_path"]
        if _sha256(path) != entry["sha256"]:
            raise ValueError(f"source checksum mismatch: {entry['local_path']}")
        text = path.read_text(encoding="utf-8")
        claims = [*_markdown_claims(text), *_html_claims(text)]
        artifacts.append(
            {
                "repository": entry["repository"],
                "local_path": entry["local_path"],
                "source_sha256": entry["sha256"],
                "annotation_method": "preregistered_independent_cross_domain_table_rule",
                "expected_claims": claims,
            }
        )
    return {
        "schema": "reprocheck.cross-domain-holdout-annotations.v1",
        "phase": "created_before_frozen_v0.7_evaluator_run",
        "preregistration_sha256": lock["preregistration_sha256"],
        "source_manifest_sha256": _sha256(MANIFEST),
        "evaluator_sha256": lock["evaluator_sha256"],
        "annotation_code_imports_reprocheck": False,
        "reviewers": {
            "rule_derived": True,
            "internal_human": 1,
            "independent_external": 0,
            "adjudication": False,
        },
        "pre_output_review": "All 18 unique table-header layouts were inventoried before evaluator execution; accepted metric headers and ambiguous exclusions were reviewed.",
        "artifacts": sorted(artifacts, key=lambda item: item["local_path"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build or verify cross-domain holdout labels")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = build()
    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(serialized, encoding="utf-8")
        action = "wrote"
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != serialized:
        print("ERROR: annotations differ; inspect and use --write before evaluator execution")
        return 1
    else:
        action = "verified"
    counts: dict[str, int] = {}
    for artifact in payload["artifacts"]:
        for claim in artifact["expected_claims"]:
            counts[claim["metric"]] = counts.get(claim["metric"], 0) + 1
    print(
        f"{action} artifacts={len(payload['artifacts'])} "
        f"claim_bearing={sum(bool(item['expected_claims']) for item in payload['artifacts'])} "
        f"claims={sum(counts.values())} metrics={dict(sorted(counts.items()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
