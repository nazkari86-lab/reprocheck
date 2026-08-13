from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Literal

from .metric_names import (
    METRIC_ALIASES,
    canonical_metric,
    is_unit_interval_metric,
    metric_family,
)
from .models import Claim, ClaimCheck

_ALIASES = "|".join(sorted((re.escape(k) for k in METRIC_ALIASES), key=len, reverse=True))
_NUMBER = r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?"
_CLAIM_RE = re.compile(
    rf"(?<![\w])(?P<metric>{_ALIASES})(?![\w])\s*(?:score|метрика)?\s*"
    rf"(?:=|:|of|at|составил[аи]?|достигл[аи]?|равна?|на\s+уровне)?"
    rf"\s*(?P<value>{_NUMBER})"
    rf"\s*(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_NUMBER_RE = re.compile(rf"(?P<value>{_NUMBER})\s*(?P<percent>%)?")
_STRUCTURED_KEY_RE = re.compile(
    rf"(?<![\w])(?P<metric>[\w²][\w².()+-]*)\s*:\s*"
    rf"(?P<value>{_NUMBER})\s*(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_COCO_SUMMARY_RE = re.compile(
    rf"Average\s+(?P<kind>Precision|Recall)\s+\((?:AP|AR)\)\s+@\[\s*"
    rf"IoU=(?P<iou>[0-9.:]+)\s*\|\s*area=\s*(?P<area>\w+)\s*\|[^]]*\]\s*=\s*"
    rf"(?P<value>{_NUMBER})",
    flags=re.IGNORECASE,
)
_DURATION_CLAIM_RE = re.compile(
    rf"(?:processing\s+time\s*[:=]|complet(?:e|ed|ing)(?:\s+the\s+(?:test|run))?\s+in)\s*"
    rf"(?P<value>{_NUMBER})\s*(?P<unit>microseconds?|µs|us|milliseconds?|ms|seconds?|secs?|s|minutes?|mins?|m)\b",
    flags=re.IGNORECASE,
)
_SPEEDUP_CLAIM_RE = re.compile(rf"(?P<value>{_NUMBER})\s*[x×]\s+faster\b", flags=re.IGNORECASE)
_PARAMETER_TOKENS = {"threshold", "thresh", "cutoff", "nms", "weight", "loss"}
_CONTEXT_HEADERS = {
    "architecture": "model",
    "average": "averaging",
    "averaging": "averaging",
    "dataset": "dataset",
    "experiment": "experiment",
    "model": "model",
    "model name": "model",
    "name": "model",
    "run": "run",
    "split": "split",
    "task": "task",
    "threshold": "threshold",
    "variant": "variant",
}


def extract_claims(text: str) -> list[Claim]:
    claims: list[Claim] = []
    text_seen: set[tuple[int, str, float]] = set()
    lines = text.splitlines()
    table_lines = _markdown_table_line_numbers(lines)
    prose_lines = _mask_html_tables(text).splitlines()
    for line_number, line in enumerate(prose_lines, start=1):
        if line_number in table_lines:
            continue
        coco_match = _COCO_SUMMARY_RE.search(line)
        if coco_match is not None:
            metric = _coco_summary_metric(coco_match)
            if metric is not None:
                value = _normalize_value(
                    metric,
                    float(coco_match.group("value").replace(",", ".")),
                    percent=False,
                )
                text_seen.add((line_number, metric, value))
                claims.append(
                    Claim(metric=metric, value=value, raw_text=line.strip(), line=line_number)
                )
            continue
        duration_matches = list(_DURATION_CLAIM_RE.finditer(line))
        for match in duration_matches:
            value = _duration_seconds(match.group("value"), match.group("unit"))
            key = (line_number, "runtime_seconds", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(
                        metric="runtime_seconds",
                        value=value,
                        raw_text=line.strip(),
                        line=line_number,
                    )
                )
        for match in _SPEEDUP_CLAIM_RE.finditer(line):
            value = float(match.group("value").replace(",", "."))
            key = (line_number, "speedup", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(metric="speedup", value=value, raw_text=line.strip(), line=line_number)
                )
        for match in _STRUCTURED_KEY_RE.finditer(line):
            metric = _structured_metric_name(match.group("metric"))
            if metric is None:
                continue
            value = _normalize_value(
                metric,
                float(match.group("value").replace(",", ".")),
                percent=bool(match.group("percent")),
            )
            key = (line_number, metric, value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(metric=metric, value=value, raw_text=line.strip(), line=line_number)
                )
        for match in _CLAIM_RE.finditer(line):
            alias = match.group("metric").lower()
            metric = METRIC_ALIASES[alias]
            if metric.endswith("_seconds") and duration_matches:
                continue
            if metric in {"iou", "hard_iou"} and _is_nms_parameter(line, match.start()):
                continue
            value = _normalize_value(
                metric,
                float(match.group("value").replace(",", ".")),
                percent=bool(match.group("percent")),
            )
            key = (line_number, metric, value)
            if key in text_seen:
                continue
            text_seen.add(key)
            claims.append(
                Claim(metric=metric, value=value, raw_text=line.strip(), line=line_number)
            )
    for claim in extract_table_claims(text):
        key = (claim.line, claim.metric, claim.value)
        if key not in text_seen:
            claims.append(claim)
    claims.sort(key=lambda claim: claim.line)
    return claims


def extract_table_claims(text: str) -> list[Claim]:
    """Extract only claims represented by Markdown or HTML table cells."""
    claims = [
        *_extract_markdown_table_claims(text.splitlines()),
        *_extract_html_table_claims(text),
    ]
    claims.sort(key=lambda claim: claim.line)
    return claims


def _markdown_table_line_numbers(lines: list[str]) -> set[int]:
    table_lines: set[int] = set()
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if not headers or not separators or not _is_separator_row(separators, headers):
            index += 1
            continue
        table_lines.update({index + 1, index + 2})
        row_index = index + 2
        while row_index < len(lines) and _split_table_row(lines[row_index]):
            table_lines.add(row_index + 1)
            row_index += 1
        index = max(row_index, index + 1)
    return table_lines


def _mask_html_tables(text: str) -> str:
    def mask(match: re.Match[str]) -> str:
        return "".join("\n" if character == "\n" else " " for character in match.group())

    return re.sub(r"<table\b[^>]*>.*?</table\s*>", mask, text, flags=re.IGNORECASE | re.DOTALL)


def _structured_metric_name(raw_name: str) -> str | None:
    canonical = canonical_metric(raw_name)
    tokens = set(re.split(r"[_.-]+", canonical))
    if tokens & _PARAMETER_TOKENS:
        return None
    family = metric_family(canonical)
    if family is None:
        return None
    return family if canonical == family else canonical


def _extract_markdown_table_claims(lines: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if not headers or not separators or not _is_separator_row(separators, headers):
            index += 1
            continue
        metrics = [_metric_from_header(header) for header in headers]
        compound_metrics = [_compound_metrics_from_header(header) for header in headers]
        row_index = index + 2
        while row_index < len(lines):
            cells = _split_table_row(lines[row_index])
            if not cells:
                break
            context = _table_context(headers, metrics, cells)
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                value = _table_value(metric, cells[column])
                if value is not None:
                    claims.append(
                        Claim(
                            metric=metric,
                            value=value,
                            raw_text=lines[row_index].strip(),
                            line=row_index + 1,
                            context=context,
                        )
                    )
            for column, compound in enumerate(compound_metrics):
                if not compound or column >= len(cells):
                    continue
                values = _compound_table_values(compound, cells[column])
                if len(values) != len(compound):
                    continue
                for metric, value in zip(compound, values, strict=True):
                    claims.append(
                        Claim(
                            metric=metric,
                            value=value,
                            raw_text=lines[row_index].strip(),
                            line=row_index + 1,
                            context=context,
                        )
                    )
            row_index += 1
        index = max(row_index, index + 1)
    return claims


def _split_table_row(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    escaped_pipe = "\x00REPROCHECK_PIPE\x00"
    stripped = line.strip().replace(r"\|", escaped_pipe)
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = [cell.replace(escaped_pipe, "|").strip() for cell in stripped.split("|")]
    return cells if len(cells) >= 2 else None


def _is_separator_row(cells: list[str], headers: list[str]) -> bool:
    normalized = [cell.replace(" ", "") for cell in cells]
    standard = all(re.fullmatch(r":?-{3,}:?", cell) for cell in normalized)
    openmmlab_accuracy = (
        all(re.fullmatch(r":?-{2,}:?", cell) for cell in normalized)
        and any("top1" in _plain_cell(header).casefold().replace(" ", "") for header in headers)
        and any("top5" in _plain_cell(header).casefold().replace(" ", "") for header in headers)
    )
    return bool(cells) and (standard or openmmlab_accuracy)


def _coco_summary_metric(match: re.Match[str]) -> str | None:
    if match.group("area").casefold() != "all":
        return None
    if match.group("kind").casefold() == "recall":
        return "ar"
    iou = match.group("iou")
    if iou == "0.50:0.95":
        return "map50_95"
    if iou == "0.50":
        return "map50"
    if iou == "0.75":
        return "map75"
    return "ap"


def _plain_cell(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!?(?:\[([^]]*)\])\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _metric_from_header(header: str) -> str | None:
    plain = _plain_cell(header).casefold().replace("_", " ")
    compact = re.sub(r"[^\w²]+", " ", plain, flags=re.UNICODE).strip()
    waymo = re.search(r"\b(maph|map)\s*l([12])\b", compact)
    if waymo:
        return f"{waymo.group(1)}_l{waymo.group(2)}"
    if re.search(r"\b(?:m\s*)?ap\b", compact) and _is_size_specific_ap(compact.split()):
        return None
    detection_metric = _detection_metric_from_header(compact)
    if detection_metric is not None:
        return detection_metric
    if re.search(r"\bmiou\b|\bmean\s+iou\b", compact):
        return "miou"
    if re.search(r"\btop\s*1\b", compact) and not re.search(r"\berr(?:or)?\b", compact):
        return "top1_accuracy"
    if re.search(r"\btop\s*5\b", compact) and not re.search(r"\berr(?:or)?\b", compact):
        return "top5_accuracy"
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        normalized_alias = re.sub(r"[^\w²]+", " ", alias.casefold(), flags=re.UNICODE).strip()
        if normalized_alias and re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", compact):
            return METRIC_ALIASES[alias]
    return None


def _compound_metrics_from_header(header: str) -> list[str] | None:
    plain = _plain_cell(header)
    if "/" not in plain:
        return None
    metrics: list[str] = []
    for part in plain.split("/"):
        canonical = canonical_metric(part)
        if metric_family(canonical) is None:
            return None
        metrics.append(canonical)
    return metrics if len(metrics) > 1 else None


def _compound_table_values(metrics: list[str], cell: str) -> list[float]:
    parts = [part.strip() for part in _plain_cell(cell).split("/")]
    if len(parts) != len(metrics):
        return []
    values: list[float] = []
    for metric, part in zip(metrics, parts, strict=True):
        match = _NUMBER_RE.fullmatch(part)
        if match is None:
            return []
        value = float(match.group("value").replace(",", "."))
        values.append(_normalize_value(metric, value, percent=bool(match.group("percent"))))
    return values


def _detection_metric_from_header(compact: str) -> str | None:
    words = compact.split()
    word_set = set(words)
    joined = "".join(words)
    prefix = None
    if word_set & {"bbox", "box"}:
        prefix = "box"
    elif word_set & {"segm", "mask"} or "segmentation" in joined:
        prefix = "mask"
    elif "proposal" in joined or "prop" in word_set:
        prefix = "proposal"
    elif "keypoint" in joined or "keypoints" in joined or "kp" in word_set:
        prefix = "keypoint"

    is_map = bool(re.search(r"\bm\s*ap\b|\bmap", compact))
    is_ap = (
        is_map or bool(re.search(r"\bap(?:\s*\d+)?\b", compact)) or "average precision" in compact
    )
    if is_ap and _is_size_specific_ap(words):
        return None
    family = None
    if is_ap and re.search(r"50\s+95", compact):
        family = "map50_95" if prefix is None else "ap50_95"
    elif is_ap and re.search(r"(?:\bap\s*|\bmap\s*)75\b|\b75\b", compact):
        family = "map75" if is_map and prefix is None else "ap75"
    elif is_ap and re.search(r"(?:\bap\s*|\bmap\s*)50\b|\b50\b", compact):
        family = "map50" if is_map and prefix is None else "ap50"
    elif is_ap:
        family = "ap"
    elif re.search(r"\bar(?:\s*\d+)?\b", compact) or "average recall" in compact:
        family = "ar"
    elif re.search(r"\bpq\b", compact) or "panoptic quality" in compact:
        family = "pq"
    if family is None:
        return None
    return f"{prefix}_{family}" if prefix else family


def _is_size_specific_ap(words: list[str]) -> bool:
    size_words = {"small", "medium", "large"}
    if set(words) & size_words:
        return True
    return bool(words and words[-1] in {"s", "m", "l"})


class _HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[tuple[list[str], int]]] = []
        self._table_depth = 0
        self._rows: list[tuple[list[str], int]] = []
        self._row: list[str] | None = None
        self._row_line = 1
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "table":
            if self._table_depth == 0:
                self._rows = []
            self._table_depth += 1
        elif self._table_depth and tag == "tr":
            self._flush_row()
            self._row = []
            self._row_line = self.getpos()[0]
        elif self._table_depth and tag in {"th", "td"}:
            if tag == "th" and self._row is None:
                self._row = []
                self._row_line = self.getpos()[0]
            self._cell = []
        elif self._cell is not None and tag == "br":
            self._cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell is not None:
            if self._row is not None:
                self._row.append(_plain_cell("".join(self._cell)))
            self._cell = None
        elif tag == "tr":
            self._flush_row()
        elif tag == "table" and self._table_depth:
            self._flush_row()
            self._table_depth -= 1
            if self._table_depth == 0 and self._rows:
                self.tables.append(self._rows)
                self._rows = []

    def _flush_row(self) -> None:
        if self._row:
            self._rows.append((self._row, self._row_line))
        self._row = None


def _extract_html_table_claims(text: str) -> list[Claim]:
    parser = _HTMLTableParser()
    parser.feed(text)
    parser.close()
    claims: list[Claim] = []
    for table in parser.tables:
        if len(table) < 2:
            continue
        headers = table[0][0]
        metrics = [_metric_from_header(header) for header in headers]
        for cells, line in table[1:]:
            context = _table_context(headers, metrics, cells)
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                value = _table_value(metric, cells[column])
                if value is not None:
                    claims.append(
                        Claim(
                            metric=metric,
                            value=value,
                            raw_text=" | ".join(cells),
                            line=line,
                            context=context,
                        )
                    )
    return claims


def _table_value(metric: str, cell: str) -> float | None:
    if metric.endswith("_seconds"):
        return _duration_cell_seconds(cell)
    matches = list(_NUMBER_RE.finditer(_plain_cell(cell)))
    if len(matches) != 1:
        return None
    match = matches[0]
    value = float(match.group("value").replace(",", "."))
    return _normalize_value(metric, value, percent=bool(match.group("percent")))


def _duration_seconds(value: str, unit: str) -> float:
    number = float(value.replace(",", "."))
    normalized = unit.casefold()
    if normalized in {"microsecond", "microseconds", "µs", "us"}:
        return number / 1_000_000
    if normalized in {"millisecond", "milliseconds", "ms"}:
        return number / 1_000
    if normalized in {"minute", "minutes", "min", "mins", "m"}:
        return number * 60
    return number


def _duration_cell_seconds(cell: str) -> float | None:
    plain = _plain_cell(cell).casefold().replace(" ", "")
    match = re.fullmatch(
        rf"(?:(?P<minutes>{_NUMBER})(?:m|min|mins|minute|minutes))?"
        rf"(?:(?P<seconds>{_NUMBER})(?:s|sec|secs|second|seconds)?)?",
        plain,
    )
    if match is None or not (match.group("minutes") or match.group("seconds")):
        return None
    minutes = float((match.group("minutes") or "0").replace(",", "."))
    seconds = float((match.group("seconds") or "0").replace(",", "."))
    return minutes * 60 + seconds


def _table_context(
    headers: list[str], metrics: list[str | None], cells: list[str]
) -> dict[str, str]:
    context: dict[str, str] = {}
    for index, header in enumerate(headers):
        if metrics[index] is not None or index >= len(cells):
            continue
        normalized_header = re.sub(
            r"[^\w]+", " ", _plain_cell(header).casefold(), flags=re.UNICODE
        ).strip()
        key = _CONTEXT_HEADERS.get(normalized_header)
        value = _plain_cell(cells[index])
        if key and value and len(value) <= 200:
            context[key] = value
    return context


def _normalize_value(metric: str, value: float, *, percent: bool) -> float:
    if percent or (is_unit_interval_metric(metric) and 1 < value <= 100):
        return value / 100.0
    return value


def _is_nms_parameter(line: str, metric_start: int) -> bool:
    prefix = line[max(0, metric_start - 12) : metric_start]
    return bool(re.search(r"\bNMS\s*$", prefix, flags=re.IGNORECASE))


def check_claims(
    claims: list[Claim],
    observed_metrics: dict[str, float],
    tolerance: float,
    evidence_levels: dict[str, Literal["reported", "recomputed"]] | None = None,
    evidence_contexts: dict[str, dict[str, str]] | None = None,
) -> list[ClaimCheck]:
    checks: list[ClaimCheck] = []
    for claim in claims:
        observed = observed_metrics.get(claim.metric)
        if observed is not None and not _contexts_compatible(
            claim.context, (evidence_contexts or {}).get(claim.metric, {})
        ):
            observed = None
        if observed is None:
            checks.append(
                ClaimCheck(
                    claim=claim,
                    status="no_evidence",
                    observed=None,
                    difference=None,
                    tolerance=tolerance,
                    evidence_level=None,
                    display_kind=(
                        "percentage" if is_unit_interval_metric(claim.metric) else "scalar"
                    ),
                )
            )
            continue
        difference = abs(claim.value - observed)
        evidence_level: Literal["reported", "recomputed"] = (evidence_levels or {}).get(
            claim.metric, "reported"
        )
        matched_status = "verified" if evidence_level == "recomputed" else "supported"
        checks.append(
            ClaimCheck(
                claim=claim,
                status=matched_status if difference <= tolerance else "mismatch",
                observed=observed,
                difference=difference,
                tolerance=tolerance,
                evidence_level=evidence_level,
                display_kind=("percentage" if is_unit_interval_metric(claim.metric) else "scalar"),
            )
        )
    return checks


def _contexts_compatible(claim: dict[str, str], evidence: dict[str, str]) -> bool:
    shared = set(claim) & set(evidence)
    return not shared or all(
        claim[key].strip().casefold() == evidence[key].strip().casefold() for key in shared
    )
