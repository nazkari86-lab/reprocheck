from __future__ import annotations

import html
import re
from collections import Counter
from html.parser import HTMLParser
from typing import Literal

from .metric_names import (
    METRIC_ALIASES,
    canonical_metric,
    is_unit_interval_metric,
    metric_family,
)
from .models import Claim, ClaimCheck

_ALIASES = "|".join(
    sorted((re.escape(k) for k in METRIC_ALIASES if k != "score"), key=len, reverse=True)
)
_NUMBER = (
    r"[+\-−]?(?:(?:\d{1,3}(?:,\d{3})+)(?:\.\d+)?|"
    r"\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+\-−]?\d+)?"
)
_CLAIM_RE = re.compile(
    rf"(?<![\w])(?P<metric>{_ALIASES})(?![\w])\s*(?:score|метрика)?\s*"
    rf"(?:=|:|of|at|составил[аи]?|достигл[аи]?|равна?|на\s+уровне)?"
    rf"\s*(?P<value>{_NUMBER})"
    rf"\s*(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_NUMBER_RE = re.compile(rf"(?P<value>{_NUMBER})\s*(?P<percent>%)?")
_STRUCTURED_KEY_RE = re.compile(
    rf"(?<![\w])(?P<metric>[\w²][\w².()+-]*)[\"']?\s*:\s*"
    rf"(?P<value>{_NUMBER})\s*(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_GENERIC_SCORE_CONTEXT_RE = re.compile(
    r"(?:\bpublished\s+result\b|\btarget\s+score\b|"
    r"\b(?:composite\s+)?fitness\s+score\b|"
    r"\bscore\s*(?:[=:≈<>]|>=|<=)|\bbenchmark(?:\s+score)?\s*(?:[=:~]|\bscore\s+of\b)|"
    r"\b(?:beat|beats|beating|match|matched|matching)\b[^\n]*\bbenchmark\b)",
    flags=re.IGNORECASE,
)
_GENERIC_SCORE_NUMBER_RE = re.compile(rf"(?<![\w])(?P<value>{_NUMBER})(?:\+)?(?![\w])")
_VALIDATOR_COUNT_RE = re.compile(
    rf"\b(?P<count>{_NUMBER}|single|one|two|three|four)"
    r"(?:-node\s+dev\s+mode\b[^\n]*|\s+local\s+validators?\b)",
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
_POSTFIX_SPEEDUP_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*(?P<percent>%)?\s+speedup\b", flags=re.IGNORECASE
)
_SPEEDUP_RANGE_RE = re.compile(
    rf"\bbeats?\b[^\n]*?\bby\s+(?P<low>{_NUMBER})\s*[–—-]\s*(?P<high>{_NUMBER})\s*%",
    flags=re.IGNORECASE,
)
_MEMORY_COMPARISON_RE = re.compile(
    rf"\b(?:cuts?|reduces?)\s+(?:resident\s+)?memory\b[^\n]*?\bto\s+(?:about|around|~)?\s*"
    rf"(?P<target>{_NUMBER})\s*(?P<target_unit>kb|mb|gb)\b[^\n]*?\bfrom\s+"
    rf"(?:about|around|~)?\s*(?P<source>{_NUMBER})\s*(?P<source_unit>kb|mb|gb)\b",
    flags=re.IGNORECASE,
)
_UNIT_DURATION_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*(?:±\s*{_NUMBER}\s*)?"
    rf"(?P<unit>nanoseconds?|ns|microseconds?|µs|us|milliseconds?|ms|"
    rf"minutes?|mins?|min|seconds?|secs?|s)\b",
    flags=re.IGNORECASE,
)
_TEST_COUNT_RE = re.compile(
    r"(?<![\w.,])(?P<value>(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*))\s+"
    r"(?:(?P<scope>Python|TypeScript)(?:\s+[Tt]ests)?|"
    r"(?:(?:passing|successful)\s+)?(?:unit\s+)?[Tt]ests)\b",
)
_MULTILINE_TEST_COUNT_RE = re.compile(
    r"(?<![\w.,])(?P<value>(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*))\s+"
    r"(?:(?:passing|successful)\s+)?(?:unit\s+)?tests\b",
    flags=re.IGNORECASE,
)
_TOTAL_TEST_COUNT_RE = re.compile(
    r"\btests\b.{0,120}?\bthere\s+are\s+"
    r"(?P<value>(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*))\s+in\s+total\b",
    flags=re.IGNORECASE | re.DOTALL,
)
_PASSED_TEST_COUNT_RE = re.compile(
    r"(?<![\w.,])(?P<value>(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*))\s+passed\b"
    r"[^\n]{0,40}\b(?:skipped|failed)\b",
    flags=re.IGNORECASE,
)
_KOREAN_TEST_COUNT_RE = re.compile(
    r"(?<![\w.,])(?P<value>(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*))\s*개\s*"
    r"(?:자동\s*)?테스트"
)
_VRAM_USAGE_RE = re.compile(
    rf"(?:peak(?:\s+(?:GPU|device))?\s+(?:memory|VRAM)|peak\s+of)\D{{0,24}}?"
    rf"(?P<value>{_NUMBER})\s*(?P<unit>kb|mb|gb)\s+(?:GPU\s+)?VRAM\b",
    flags=re.IGNORECASE,
)
_ARTIFACT_SIZE_COMPARISON_RE = re.compile(
    rf"\b(?:hashfile|artifact|file)\b[^\n()]*\([^\n)]*?"
    rf"(?P<first>{_NUMBER})\s+(?:vs\.?|versus)\s+(?P<second>{_NUMBER})\s*"
    rf"(?P<unit>kib|mib|gib)\b",
    flags=re.IGNORECASE,
)
_RANKED_PROSE_RE = re.compile(
    rf"(?<![\w])(?P<family>map|mar|mrr|mndcg|ndcg|precision|recall)\s*@\s*"
    rf"(?P<k>[1-9]\d*)(?:\s*(?:=|:)\s*|\s+)(?P<value>{_NUMBER})\s*(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_SEPARABILITY_RE = re.compile(
    rf"\b(?:embedding\s+)?separability\s*(?:delta|[Δδ])?\s*(?:=|:)?\s*"
    rf"(?P<value>{_NUMBER})",
    flags=re.IGNORECASE,
)
_THROUGHPUT_BOOST_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*[x×]\s+(?:throughput\s+)?boost\b", re.IGNORECASE
)
_OPTIMAL_THROUGHPUT_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*\\?%\s+of\s+optimal\s+throughput", re.IGNORECASE
)
_OPTIMAL_THROUGHPUT_RANGE_RE = re.compile(
    rf"(?P<low>{_NUMBER})\s*\\?%\s+(?:to|[-–—])\s*(?P<high>{_NUMBER})\s*\\?%\s+"
    r"of\s+optimal\s+throughput",
    re.IGNORECASE,
)
_METRIC_IMPROVEMENT_RE = re.compile(
    rf"(?P<metric>Aff[- ]?F1|Weighted\s+F1|F1|AUC|BLEU|ROUGE[- ]?L)"
    rf"(?:\s+scores?)?[^.;,]{{0,35}}?(?:by|of)\s+(?P<value>{_NUMBER})\s*\\?%",
    re.IGNORECASE,
)
_PERCENT_IN_METRIC_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*\\?%\s+in\s+(?P<metric>BLEU|ROUGE[- ]?L|F1)(?:\s+scores?)?",
    re.IGNORECASE,
)
_POSTFIX_METRIC_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*%\s+(?:image-level\s+|pixel-level\s+)?"
    rf"(?P<metric>AU[- ]?ROC|PRO)\b",
    re.IGNORECASE,
)
_BEST_METRIC_RE = re.compile(
    rf"(?<![\w_])(?:best\s+)?(?P<metric>F1(?:\s+score)?|accuracy|precision|recall|"
    rf"specificity|AUC|AUROC|IoU|Dice)(?![\w_])(?:\s+(?:score|coefficient))?\s*"
    rf"(?:achieved[^:;]{{0,80}})?\s*:\s*(?P<value>{_NUMBER})\s*(?P<percent>%)?",
    re.IGNORECASE,
)
_FRAGMENTED_MEMORY_RE = re.compile(
    rf"Fragmented\s+Memory:\s*(?P<memory>{_NUMBER})\s*(?P<unit>GB|MB)\s*"
    rf"\((?P<ratio>{_NUMBER})\s*%\)",
    re.IGNORECASE,
)
_MAX_BATCH_RE = re.compile(rf"maximum\s+batch\s+size\s+is\s+(?P<value>{_NUMBER})", re.I)
_OOM_BATCH_RE = re.compile(rf"OOM\s+with\s+(?P<value>{_NUMBER})", re.I)
_ASSERTION_TEST_RE = re.compile(
    rf"(?P<assertions>{_NUMBER})\s+assertions?\s+in\s+(?P<tests>{_NUMBER})\s+test\s+cases?",
    re.IGNORECASE,
)
_WRK_LATENCY_RE = re.compile(
    rf"^\s*Latency\s+(?P<avg>{_NUMBER})(?P<unit>us|µs|ms|s)\s+"
    rf"(?P<stdev>{_NUMBER})(?P=unit)\s+(?P<max>{_NUMBER})(?P=unit)\s+"
    rf"(?P<within>{_NUMBER})%",
    re.IGNORECASE,
)
_WRK_REQ_RE = re.compile(
    rf"^\s*Req/Sec\s+(?P<avg>{_NUMBER})(?P<avg_scale>[kKmM]?)\s+"
    rf"(?P<stdev>{_NUMBER})(?P<stdev_scale>[kKmM]?)\s+"
    rf"(?P<max>{_NUMBER})(?P<max_scale>[kKmM]?)\s+(?P<within>{_NUMBER})%",
    re.IGNORECASE,
)
_WRK_TOTAL_RE = re.compile(
    rf"(?P<requests>{_NUMBER})\s+requests\s+in\s+(?P<seconds>{_NUMBER})s,\s*"
    rf"(?P<data>{_NUMBER})(?P<unit>KB|MB|GB)\s+read",
    re.IGNORECASE,
)
_REQUESTS_PER_SECOND_RE = re.compile(rf"Requests/sec:\s*(?P<value>{_NUMBER})", re.I)
_RESULT_COUNT_RE = re.compile(
    rf"processed\s+(?P<processed>{_NUMBER})\s+tokens\s+with\s+(?P<phrases>{_NUMBER})\s+phrases;\s*"
    rf"found:\s*(?P<found>{_NUMBER})\s+phrases;\s*correct:\s*(?P<correct>{_NUMBER})",
    re.IGNORECASE,
)
_TRAILING_FOUND_COUNT_RE = re.compile(rf"\bFB1:\s*{_NUMBER}\s+(?P<found>{_NUMBER})\s*$", re.I)
_PAREN_PERCENT_RE = re.compile(rf"\((?:~\s*)?(?P<value>{_NUMBER})\s*\\?%\)")
_ARTIFACT_SIZE_RE = re.compile(
    rf"(?:requir(?:es|ing)|artifact(?:\s+size)?(?:\s+is)?)[^\n]{{0,24}}?(?P<value>{_NUMBER})\s*"
    rf"(?P<unit>KB|MB|GB)\b",
    re.IGNORECASE,
)
_BATCH_SPEEDUP_RE = re.compile(
    rf"(?:increase|increases|increased)[^\n]{{0,40}}?batch\s+size\s+by\s+(?P<value>{_NUMBER})\s*[x×]",
    re.IGNORECASE,
)
_CALIBRATION_RE = re.compile(
    rf"mean\s+lat\.:\s*(?P<latency>{_NUMBER})\s*(?P<latency_unit>usec|us|µs|ms),\s*"
    rf"rate\s+sampling\s+interval:\s*(?P<interval>{_NUMBER})\s*(?P<interval_unit>msec|ms|us|µs)",
    re.IGNORECASE,
)
_APPROXIMATE_METRIC_RE = re.compile(
    rf"(?P<metric>accuracy|precision|recall|F1|AUC|IoU|Dice)[^.;:]{{0,45}}?"
    rf"\(?~\s*(?P<value>{_NUMBER})\s*\\?%\)?",
    re.IGNORECASE,
)
_PAIRED_STDEV_RE = re.compile(
    rf"standard\s+deviations?\s+of\s+(?P<first>{_NUMBER})\s+and\s+"
    rf"(?P<second>{_NUMBER})\s*,?\s+respectively",
    re.IGNORECASE,
)
_FRAGMENTATION_BOUND_RE = re.compile(
    rf"(?:decrease|decreases|decreased)[^.;]{{0,40}}?fragmentation\s+to\s*"
    rf"(?P<comparator><=|<|~)?\s*(?P<value>{_NUMBER})\s*\\?%",
    re.IGNORECASE,
)
_RANKED_ARROW_RE = re.compile(
    rf"(?<![\w])(?P<family>map|mar|mrr|mndcg|ndcg|precision|recall)\s*@\s*"
    rf"(?P<k>[1-9]\d*)[^\n|]*?[→➜]\s*(?P<value>{_NUMBER})\s*(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_PARAMETER_TOKENS = {"threshold", "thresh", "cutoff", "nms", "weight", "loss"}
_CONTEXT_HEADERS = {
    "architecture": "model",
    "average": "averaging",
    "averaging": "averaging",
    "benchmark": "system",
    "dataset": "dataset",
    "experiment": "experiment",
    "model": "model",
    "model name": "model",
    "name": "model",
    "provider": "system",
    "run": "run",
    "runtime": "system",
    "split": "split",
    "task": "task",
    "serialization type": "system",
    "threshold": "threshold",
    "variant": "variant",
}


def extract_claims(text: str) -> list[Claim]:
    claims: list[Claim] = []
    text_seen: set[tuple[int, str, float]] = set()
    lines = text.splitlines()
    for match in _MULTILINE_TEST_COUNT_RE.finditer(text):
        if "\n" not in match.group():
            continue
        value = _parse_number(match.group("value"))
        line_number = text.count("\n", 0, match.start()) + 1
        raw_text = " ".join(match.group().split())
        text_seen.add((line_number, "test_count", value))
        claims.append(
            Claim(
                metric="test_count",
                value=value,
                raw_text=raw_text,
                line=line_number,
                context={"scope": "total"},
            )
        )
    for match in _TOTAL_TEST_COUNT_RE.finditer(text):
        value = _parse_number(match.group("value"))
        line_number = text.count("\n", 0, match.start("value")) + 1
        key = (line_number, "test_count", value)
        if key not in text_seen:
            text_seen.add(key)
            claims.append(
                Claim(
                    metric="test_count",
                    value=value,
                    raw_text=" ".join(match.group().split()),
                    line=line_number,
                    context={"scope": "total"},
                )
            )
    table_lines = _markdown_table_line_numbers(lines)
    prose_lines = _mask_html_tables(text).splitlines()
    for line_number, raw_line in enumerate(prose_lines, start=1):
        if line_number in table_lines:
            continue
        line = _plain_cell(raw_line)
        coco_match = _COCO_SUMMARY_RE.search(line)
        if coco_match is not None:
            metric = _coco_summary_metric(coco_match)
            if metric is not None:
                value = _normalize_value(
                    metric,
                    _parse_number(coco_match.group("value")),
                    percent=False,
                )
                text_seen.add((line_number, metric, value))
                claims.append(
                    Claim(metric=metric, value=value, raw_text=raw_line.strip(), line=line_number)
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
                        raw_text=raw_line.strip(),
                        line=line_number,
                    )
                )
        for match in _SPEEDUP_CLAIM_RE.finditer(line):
            value = _parse_number(match.group("value"))
            key = (line_number, "speedup", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(
                        metric="speedup", value=value, raw_text=raw_line.strip(), line=line_number
                    )
                )
        for match in _POSTFIX_SPEEDUP_RE.finditer(line):
            value = _normalize_value(
                "speedup", _parse_number(match.group("value")), percent=bool(match.group("percent"))
            )
            key = (line_number, "speedup", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(
                        metric="speedup", value=value, raw_text=raw_line.strip(), line=line_number
                    )
                )
        for match in _SPEEDUP_RANGE_RE.finditer(line):
            for metric, group in (("speedup_range_low", "low"), ("speedup_range_high", "high")):
                value = _parse_number(match.group(group)) / 100.0
                key = (line_number, metric, value)
                if key not in text_seen:
                    text_seen.add(key)
                    claims.append(
                        Claim(
                            metric=metric, value=value, raw_text=raw_line.strip(), line=line_number
                        )
                    )
        for match in _MEMORY_COMPARISON_RE.finditer(line):
            roles = (
                ("target", "target_unit", "native UI"),
                ("source", "source_unit", "webview UI"),
            )
            for value_group, unit_group, system in roles:
                value = _memory_mb(match.group(value_group), match.group(unit_group))
                key = (line_number, "memory_mb", value)
                if key not in text_seen:
                    text_seen.add(key)
                    claims.append(
                        Claim(
                            metric="memory_mb",
                            value=value,
                            raw_text=raw_line.strip(),
                            line=line_number,
                            context={"system": system},
                        )
                    )
        for match in _TEST_COUNT_RE.finditer(line):
            value = _parse_number(match.group("value"))
            key = (line_number, "test_count", value)
            if key not in text_seen:
                text_seen.add(key)
                context = (
                    {"scope": match.group("scope")} if match.group("scope") else {"scope": "total"}
                )
                claims.append(
                    Claim(
                        metric="test_count",
                        value=value,
                        raw_text=raw_line.strip(),
                        line=line_number,
                        context=context,
                    )
                )
        for count_pattern in (_PASSED_TEST_COUNT_RE, _KOREAN_TEST_COUNT_RE):
            for match in count_pattern.finditer(line):
                value = _parse_number(match.group("value"))
                key = (line_number, "test_count", value)
                if key not in text_seen:
                    text_seen.add(key)
                    claims.append(
                        Claim(
                            metric="test_count",
                            value=value,
                            raw_text=raw_line.strip(),
                            line=line_number,
                            context={"scope": "total"},
                        )
                    )
        for match in _VRAM_USAGE_RE.finditer(line):
            value = _memory_mb(match.group("value"), match.group("unit"))
            key = (line_number, "memory_mb", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(
                        metric="memory_mb", value=value, raw_text=raw_line.strip(), line=line_number
                    )
                )
        for match in _ARTIFACT_SIZE_COMPARISON_RE.finditer(line):
            factor = {"kib": 1 / 1024, "mib": 1, "gib": 1024}[match.group("unit").casefold()]
            for group, system in (("first", "reported artifact"), ("second", "baseline artifact")):
                value = _parse_number(match.group(group)) * factor
                key = (line_number, "artifact_size_mb", value)
                if key not in text_seen:
                    text_seen.add(key)
                    claims.append(
                        Claim(
                            metric="artifact_size_mb",
                            value=value,
                            raw_text=raw_line.strip(),
                            line=line_number,
                            context={"system": system},
                        )
                    )
        for match in _RANKED_PROSE_RE.finditer(line):
            family = match.group("family").casefold()
            metric = f"{family}_{match.group('k')}"
            value = _normalize_value(
                metric,
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            key = (line_number, metric, value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(metric=metric, value=value, raw_text=raw_line.strip(), line=line_number)
                )
        for match in _RANKED_ARROW_RE.finditer(line):
            metric = f"{match.group('family').casefold()}_{match.group('k')}"
            value = _normalize_value(
                metric,
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            key = (line_number, metric, value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(metric=metric, value=value, raw_text=raw_line.strip(), line=line_number)
                )
        for match in _SEPARABILITY_RE.finditer(line):
            value = _parse_number(match.group("value"))
            key = (line_number, "separability_delta", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(
                        metric="separability_delta",
                        value=value,
                        raw_text=raw_line.strip(),
                        line=line_number,
                    )
                )
        for match in _VALIDATOR_COUNT_RE.finditer(line):
            value = _count_value(match.group("count"))
            key = (line_number, "validator_count", value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(
                        metric="validator_count",
                        value=value,
                        raw_text=raw_line.strip(),
                        line=line_number,
                    )
                )
        for match in _STRUCTURED_KEY_RE.finditer(line):
            metric = _structured_metric_name(match.group("metric"))
            if metric is None:
                continue
            value = _normalize_value(
                metric,
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            key = (line_number, metric, value)
            if key not in text_seen:
                text_seen.add(key)
                claims.append(
                    Claim(metric=metric, value=value, raw_text=raw_line.strip(), line=line_number)
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
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            key = (line_number, metric, value)
            if key in text_seen:
                continue
            text_seen.add(key)
            claims.append(
                Claim(metric=metric, value=value, raw_text=raw_line.strip(), line=line_number)
            )
        has_specific_metric = any(
            seen_line == line_number and seen_metric != "score"
            for seen_line, seen_metric, _ in text_seen
        )
        if _GENERIC_SCORE_CONTEXT_RE.search(line) and not has_specific_metric:
            for match in _GENERIC_SCORE_NUMBER_RE.finditer(line):
                value = _parse_number(match.group("value"))
                key = (line_number, "score", value)
                if key not in text_seen:
                    text_seen.add(key)
                    claims.append(
                        Claim(
                            metric="score", value=value, raw_text=raw_line.strip(), line=line_number
                        )
                    )
    for claim in extract_table_claims(text):
        key = (claim.line, claim.metric, claim.value)
        if key not in text_seen:
            claims.append(claim)
    for claim in _extract_tsv_claims(text):
        key = (claim.line, claim.metric, claim.value)
        if key not in text_seen:
            claims.append(claim)
    for claim in _extract_general_result_claims(text):
        key = (claim.line, claim.metric, claim.value)
        if key not in text_seen:
            text_seen.add(key)
            claims.append(claim)
    for claim in _extract_generic_benchmark_claims(text):
        key = (claim.line, claim.metric, claim.value)
        if key not in text_seen:
            text_seen.add(key)
            claims.append(claim)
    existing_counts = Counter((claim.line, claim.metric, claim.value) for claim in claims)
    extended_counts: Counter[tuple[int, str, float]] = Counter()
    for claim in _extract_extended_benchmark_claims(text):
        key = (claim.line, claim.metric, claim.value)
        extended_counts[key] += 1
        if extended_counts[key] > existing_counts[key]:
            claims.append(claim)
    portable_counts: Counter[tuple[int, str, float]] = Counter()
    combined_counts = Counter(
        (
            claim.line,
            (
                _portable_duration_metric(claim.raw_text, claim.raw_text)
                or "avg_latency_seconds"
            )
            if claim.metric == "runtime_seconds"
            and "latency" in _plain_cell(claim.raw_text).casefold()
            else claim.metric,
            claim.value,
        )
        for claim in claims
    )
    for claim in _extract_portable_result_claims(text):
        key = (claim.line, claim.metric, claim.value)
        portable_counts[key] += 1
        if combined_counts[key] == 0 and portable_counts[key] == 1:
            claims.append(claim)
    suppressed = _suppressed_benchmark_claims(text)
    header_lines = _markdown_table_header_lines(text.splitlines()) | _delimited_table_header_lines(
        text.splitlines()
    )
    specialized = {(claim.line, claim.metric, round(claim.value, 12)) for claim in claims}
    claims = [
        claim
        for claim in claims
        if (claim.line, claim.metric, round(claim.value, 12)) not in suppressed
        and claim.line not in header_lines
        and not (
            claim.metric == "throughput_ops_per_second"
            and (claim.line, "vectors_per_second", round(claim.value, 12)) in specialized
        )
        and not (
            claim.metric in {"val_loss", "val_accuracy"}
            and (
                claim.line,
                {"val_loss": "validation_loss", "val_accuracy": "validation_accuracy"}[
                    claim.metric
                ],
                round(claim.value, 12),
            )
            in specialized
        )
        and not (
            claim.metric == "runtime_seconds"
            and claim.value < 0
            and "sub-" in _plain_cell(claim.raw_text).casefold()
            and (claim.line, "runtime_seconds", round(abs(claim.value), 12)) in specialized
        )
        and not (
            claim.metric == "ap"
            and any(
                (claim.line, metric, round(claim.value, 12)) in specialized
                for metric in ("map25", "map50")
            )
        )
        and not (
            claim.metric in {"avg_latency_seconds", "runtime_seconds"}
            and re.search(r"\bp(?:50|90|95|99(?:\.\d+)?)\b", _plain_cell(claim.raw_text), re.I)
            and any(
                (claim.line, metric, round(claim.value, 12)) in specialized
                for metric in (
                    "p50_latency_seconds",
                    "p90_latency_seconds",
                    "p95_latency_seconds",
                    "p99_latency_seconds",
                )
            )
        )
    ]
    claims = [
        Claim(
            (
                _portable_duration_metric(claim.raw_text, claim.raw_text)
                or "avg_latency_seconds"
            )
            if claim.metric == "runtime_seconds"
            and "latency" in _plain_cell(claim.raw_text).casefold()
            else claim.metric,
            abs(claim.value) if "sub-" in _plain_cell(claim.raw_text).casefold() else claim.value,
            claim.raw_text,
            claim.line,
            claim.context,
        )
        for claim in claims
    ]
    structured_pairs = {(claim.metric, claim.value) for claim in claims if claim.context}
    claims = [
        claim
        for claim in claims
        if claim.context
        or (claim.metric, claim.value) not in structured_pairs
        or not re.search(
            rf"\byield\s+(?:an?\s+)?{re.escape(claim.metric.replace('_', ' '))}\b",
            _plain_cell(claim.raw_text),
            flags=re.IGNORECASE,
        )
    ]
    excluded_systems = {
        "claimed",
        "target",
        "expected",
        "threshold",
        "goal",
        "status",
        "note",
        "ratio",
        "improvement",
        "change",
        "delta",
        "gap",
    }
    claims = [
        claim
        for claim in claims
        if claim.context.get("system", "").casefold() not in excluded_systems
        and claim.context.get("implementation", "").casefold() not in excluded_systems
        and not (
            claim.metric == "speedup"
            and re.search(r"\bfaster\s+than\s+(?:the\s+)?target\b", claim.raw_text, re.I)
        )
        and not (
            claim.metric == "throughput_ops_per_second"
            and "clients:" in claim.raw_text.casefold()
            and all(
                round(claim.value, 12) != round(_parse_number(match.group("value")), 12)
                for match in re.finditer(
                    rf"(?P<value>{_NUMBER})\s*(?:msg(?:s)?|ops?|files?|records?|rows?)\s*/\s*s\b",
                    _plain_cell(claim.raw_text),
                    re.I,
                )
            )
        )
        and not (
            claim.metric == "throughput_ops_per_second"
            and re.search(r"\breq(?:uests?)?\s*/\s*sec\b", claim.raw_text, re.I)
        )
        and not (
            claim.metric == "speedup"
            and re.search(r"\b(?:better|faster)\b", claim.raw_text, re.I)
            and "|" in claim.raw_text
        )
        and not (
            claim.metric == "throughput_ops_per_second"
            and (claim.line, "tokens_per_second", round(claim.value, 12)) in specialized
        )
        and not (
            is_unit_interval_metric(claim.metric)
            and not claim.metric.endswith("_stdev")
            and not claim.metric.endswith(("_improvement", "_decline"))
            and not 0 <= claim.value <= 1
        )
        and not (
            is_unit_interval_metric(claim.metric)
            and not claim.metric.endswith("_stdev")
            and claim.value > 1
            and re.search(r"\(\s*\d+\s*/\s*\d+", claim.raw_text)
        )
    ]
    structured_pairs = {(claim.metric, claim.value) for claim in claims if claim.context}
    claims = [
        claim
        for claim in claims
        if claim.context
        or (claim.metric, claim.value) not in structured_pairs
        or not re.search(
            r"\b(?:success|runtime|duration|memory|latency|time)\b", claim.raw_text, re.I
        )
    ]
    structured_percentiles = {
        (claim.line, claim.metric, round(claim.value, 12)) for claim in claims if claim.context
    }
    claims = [
        claim
        for claim in claims
        if not (
            not claim.context
            and claim.metric in {"avg_latency_seconds", "runtime_seconds"}
            and re.search(r"\bp(?:50|90|95|99(?:\.\d+)?)\b", claim.raw_text, re.I)
            and any(
                (claim.line, metric, round(claim.value, 12)) in structured_percentiles
                for metric in (
                    "p50_latency_seconds",
                    "p90_latency_seconds",
                    "p95_latency_seconds",
                    "p99_latency_seconds",
                )
            )
        )
    ]
    claims.sort(key=lambda claim: claim.line)
    return claims


def _extract_extended_benchmark_claims(text: str) -> list[Claim]:
    """Parse generic result structures that preserve metric semantics and units."""
    lines = text.splitlines()
    claims = _extract_extended_markdown_tables(lines)
    claims.extend(_extract_embedded_delimited_tables(lines))
    claims.extend(_extract_extended_console_claims(lines))
    claims.extend(_extract_extended_result_prose(lines))
    return claims


def _portable_header_metric(header: str) -> str | None:
    """Map common result-table headers to the stable public metric ontology."""
    plain = _plain_cell(header).casefold()
    compact = re.sub(r"[^a-z0-9]+", " ", plain).strip()
    if re.search(r"\b(?:source|answer|document)\s+match\s+within\s+top\b", compact):
        return "hit_rate"
    if any(
        word in compact
        for word in (
            "expected",
            "target",
            "threshold",
            "status",
            "improvement",
            "change",
            "delta",
            "gap",
        )
    ):
        return None
    if re.search(r"\btop\s*[15]\b", compact) or "/" in plain:
        return None
    if re.search(r"\bmacro\s+f1\b", compact):
        return "macro_f1"
    if re.search(r"\bmacro\s+(?:prec|precision)\b", compact):
        return "macro_precision"
    if re.search(r"\bmacro\s+(?:rec|recall)\b", compact):
        return "macro_recall"
    if re.search(
        r"\bhit\s*@?\s*\d+\b|\bhit\s*rate\b|\b(?:source|answer|document)\s+match\s+within\s+top\b",
        compact,
    ):
        return "hit_rate"
    if re.search(r"\bmrr\b", compact):
        return "mrr"
    if re.search(
        r"\b(?:runtime\s+)?errors?\b|\b(?:runtime\s+)?error\s+rate\b|"
        r"\bfailure\s+rate\b",
        compact,
    ):
        return "fail_rate"
    if re.search(r"\bsuccess\s+rate\b", compact):
        return "success_rate"
    if re.search(r"\b(?:prec|precision)\b", compact):
        return "precision"
    if re.search(r"\b(?:rec|recall|sensitivity)\b", compact):
        return "recall"
    if re.search(r"\bf1\b", compact):
        return "f1"
    if "accuracy" in compact or re.search(r"\bacc\b", compact):
        return "accuracy"
    if "avg response length" in compact and "token" in compact:
        return "mean_tokens"
    if "avg response length" in compact and "char" in compact:
        return "mean_chars"
    if re.search(r"\b(?:fps|frames per second)\b", compact):
        return "frames_per_second"
    if re.search(r"\b(?:requests?|req)\s*(?:/|per\s+)\s*(?:s|sec|second)\b", plain):
        return "requests_per_second"
    if re.search(r"\b(?:throughput|requests?|req)\b", compact) and re.search(
        r"\b(?:msg|ops|files?|records?|rows?)\s*(?:/|per\s*)\s*(?:s|sec|second)\b",
        plain,
    ):
        return "throughput_ops_per_second"
    if re.search(r"\b(?:avg|average|mean)\s+(?:retrieval\s+)?latency\b", compact):
        return "avg_latency_seconds"
    if re.search(r"\b(?:p50\s+(?:retrieval\s+)?latency|latency\s+p50)\b", compact):
        return "p50_latency_seconds"
    if re.search(r"\b(?:p95\s+(?:retrieval\s+)?latency|latency\s+p95)\b", compact):
        return "p95_latency_seconds"
    if re.search(r"\b(?:p99\s+(?:retrieval\s+)?latency|latency\s+p99)\b", compact):
        return "p99_latency_seconds"
    if re.search(r"\bmax(?:imum)?\s+(?:retrieval\s+)?latency\b", compact):
        return "max_latency_seconds"
    if re.search(r"\bpeak\s+(?:rss\s+)?memory\b", compact):
        return "peak_rss_mb"
    if compact in {"mean ms", "mean_ms"}:
        return "avg_latency_seconds"
    if compact in {"p50 ms", "p50_ms"}:
        return "p50_latency_seconds"
    if compact in {"p95 ms", "p95_ms"}:
        return "p95_latency_seconds"
    if compact in {"p99 ms", "p99_ms"}:
        return "p99_latency_seconds"
    if "latency" in compact or "time request" in compact:
        return "avg_latency_seconds"
    if (
        compact in {"measured time", "time", "duration", "runtime"}
        or "time per" in compact
        or compact.startswith("total training time")
        or compact.startswith("wall time")
        or compact.startswith("avg time")
    ):
        return "runtime_seconds"
    if "perplexity" in compact:
        return "perplexity"
    if compact in {"mean", "mean score"}:
        return "score"
    if "validation loss" in compact or compact in {"val loss", "val_loss"}:
        return "validation_loss"
    if compact == "loss":
        return "loss"
    return None


def _portable_cell_values(metric: str, header: str, cell: str) -> list[tuple[str, float]]:
    plain = _plain_cell(cell)
    if not plain or plain.casefold() in {"n/a", "na", "baseline", "-", "—"}:
        return []
    if metric in {"requests_per_second", "throughput_ops_per_second"}:
        quantity = re.search(
            rf"(?P<low>{_NUMBER})(?:\s*(?:to|[-–—])\s*(?P<high>{_NUMBER}))?\s*"
            r"(?P<scale>[kKmMgG]?)\s*(?:req(?:uests?)?|msg(?:s)?|ops?)\s*/\s*"
            r"s(?:ec(?:ond)?s?)?\b",
            plain,
            re.I,
        )
        if quantity is not None:
            scale = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0, "g": 1_000_000_000.0}[
                quantity.group("scale").casefold()
            ]
            values = [quantity.group("low")]
            if quantity.group("high") is not None:
                values.append(quantity.group("high"))
            return [(metric, _parse_number(value) * scale) for value in values]
    if is_unit_interval_metric(metric):
        interval = re.fullmatch(
            rf"\s*(?:<|<=|~|≈)?\s*(?P<low>{_NUMBER})\s*(?:to|[-–—])\s*"
            rf"(?P<high>{_NUMBER})\s*%?\s*",
            plain,
            re.I,
        )
        if interval is not None:
            percent = "%" in plain
            return [
                (metric, _normalize_value(metric, _parse_number(interval.group("low")), percent=percent)),
                (metric, _normalize_value(metric, _parse_number(interval.group("high")), percent=percent)),
            ]
    if metric.endswith("_seconds"):
        duration_match = _UNIT_DURATION_RE.search(plain)
        if duration_match is not None:
            return [
                (
                    metric,
                    _duration_seconds(duration_match.group("value"), duration_match.group("unit")),
                )
            ]
        unit_match = re.search(
            r"(?:^|[^a-z])(ns|us|µs|ms|s|sec|seconds?)(?:$|[^a-z])", header, re.I
        )
        if unit_match is not None:
            unit = unit_match.group(1)
        elif re.search(r"(?:^|_)ms(?:$|_)", header, re.I):
            unit = "ms"
        else:
            return []
        values = [_parse_number(match.group("value")) for match in _NUMBER_RE.finditer(plain)]
        return [(metric, _duration_seconds(str(value), unit)) for value in values[:1]]
    values = [_parse_number(match.group("value")) for match in _NUMBER_RE.finditer(plain)]
    if not values:
        return []
    normalized = [_normalize_value(metric, value, percent="%" in plain) for value in values]
    if "±" in plain and len(normalized) >= 2 and metric in {"loss", "validation_loss"}:
        return [(metric, normalized[0]), (f"{metric}_stdev", normalized[1])]
    return [(metric, normalized[0])]


def _portable_row_metric(label: str, values: list[str]) -> str | None:
    """Resolve a row label from an explicitly unit-labelled result value."""
    metric = _portable_header_metric(label)
    if metric is not None:
        return metric
    compact = re.sub(r"[^a-z0-9]+", " ", _plain_cell(label).casefold()).strip()
    value_text = " ".join(_plain_cell(value) for value in values).casefold()
    if "throughput" in compact:
        if re.search(r"\breq(?:uests?)?\s*/\s*s", value_text):
            return "requests_per_second"
        if re.search(r"\b(?:msg(?:s)?|ops?)\s*/\s*s", value_text):
            return "throughput_ops_per_second"
    if "memory" in compact and re.search(r"\b(?:kb|mb|gb)\b", value_text):
        return "memory_mb"
    return None


def _portable_outcome_columns(headers: list[str], start: int) -> list[int]:
    """Select measured result columns and reject goals, narrative notes, and ratios."""
    candidates = list(range(start, len(headers)))
    normalized = [_plain_cell(header).casefold() for header in headers]
    excluded_words = (
        "expected",
        "target",
        "threshold",
        "goal",
        "claimed",
        "status",
        "note",
        "ratio",
        "improvement",
        "change",
        "delta",
        "gap",
    )
    candidates = [
        column
        for column in candidates
        if not any(word in normalized[column] for word in excluded_words)
    ]
    observed = ("measured", "achieved", "observed", "result")
    measured = [
        column for column in candidates if any(word in normalized[column] for word in observed)
    ]
    return measured or candidates


def _portable_duration_metric(label: str, nearby: str) -> str | None:
    """Resolve a duration label without guessing a metric from its magnitude."""
    compact = re.sub(r"[^a-z0-9]+", " ", _plain_cell(label).casefold()).strip()
    context = f"{compact} {nearby.casefold()}"
    if re.search(r"\bp99\b", compact):
        return "p99_latency_seconds"
    if re.search(r"\bp95\b", compact):
        return "p95_latency_seconds"
    if re.search(r"\bp90\b", compact):
        return "p90_latency_seconds"
    if re.search(r"\bp50\b|\bmedian\b", compact):
        return "p50_latency_seconds"
    if re.search(r"\bmin(?:imum)?\b", compact) and "latency" in context:
        return "min_latency_seconds"
    if re.search(r"\bmax(?:imum)?\b", compact) and "latency" in context:
        return "max_latency_seconds"
    if re.search(r"\b(?:std|standard deviation)\b", compact) and "latency" in context:
        return "latency_stdev_seconds"
    if re.search(r"\b(?:mean|avg|average)\b", compact) and "latency" in context:
        return "avg_latency_seconds"
    if re.search(r"\b(?:connection|message)\s+time\b", compact):
        return "avg_latency_seconds"
    if "latency" in compact:
        return "avg_latency_seconds"
    if any(token in compact for token in ("time", "duration", "result", "elapsed")):
        return "runtime_seconds"
    return None


def _portable_inline_outcomes(plain: str, nearby: str) -> list[tuple[str, float]]:
    """Extract explicitly labelled prose results in both metric-value orders."""
    outcomes: list[tuple[str, float]] = []
    for match in re.finditer(
        rf"\b(?:overall|final|test)\s+(?P<label>accuracy|precision|recall|f1(?:\s+score)?)"
        rf"\s*:\s*(?P<first>{_NUMBER})\s*%[^\n]*?\b(?P<second>{_NUMBER})\s*%",
        plain,
        re.I,
    ):
        metric = _portable_header_metric(match.group("label"))
        if metric is not None:
            outcomes.extend(
                (
                    (metric, _normalize_value(metric, _parse_number(value), percent=True))
                    for value in (match.group("first"), match.group("second"))
                )
            )
    for match in re.finditer(
        rf"(?P<value>{_NUMBER})\s*%\s+(?P<label>"
        r"(?:(?:[a-z][a-z-]*\s+){0,4})(?:precision|recall|accuracy|f1(?:\s+score)?|"
        r"mrr(?:\s*@?\s*\d+)?|hit\s*@?\s*\d+|hit\s*rate|success\s*rate|"
        r"failure\s*rate|(?:runtime\s+)?errors?))\b",
        plain,
        re.I,
    ):
        metric = _portable_header_metric(match.group("label"))
        if metric is not None:
            outcomes.append(
                (
                    metric,
                    _normalize_value(metric, _parse_number(match.group("value")), percent=True),
                )
            )
    for match in re.finditer(
        rf"(?P<label>p(?:50|90|95|99)|median|min(?:imum)?|mean|average|avg|"
        r"standard deviation|std(?:\s+dev)?|(?:avg\s+)?(?:detection|reshape)|"
        r"(?:connection|message)\s+time|(?:max(?:imum)?\s+)?latency|"
        r"time(?:\s+per\s+\w+)?|wall\s+time|duration|result|elapsed)"
        r"(?:\s*:\s*|\s+(?:(?:is|was|remains|stays)(?:\s+[a-z-]+){0,4}\s+"
        r"(?:at|under|below|of)?|under|below|at|of)\s*)?\(?\s*(?:~|≈|<)?\s*"
        rf"(?P<value>{_NUMBER})\s*(?P<unit>ns|µs|us|ms|s|sec(?:ond)?s?|min(?:ute)?s?)\b",
        plain,
        re.I,
    ):
        metric = _portable_duration_metric(match.group("label"), nearby)
        if metric is not None:
            outcomes.append(
                (metric, _duration_seconds(match.group("value"), match.group("unit")))
            )
    for match in re.finditer(
        rf"(?P<value>{_NUMBER})\s*(?P<unit>ns|µs|us|ms|s|sec(?:ond)?s?|min(?:ute)?s?)\s*"
        r"(?P<label>p(?:50|90|95|99)|median|min(?:imum)?|mean|average|avg|"
        r"standard deviation|std(?:\s+dev)?|(?:max(?:imum)?\s+)?latency)\b",
        plain,
        re.I,
    ):
        metric = _portable_duration_metric(match.group("label"), f"{nearby} {plain}")
        if metric is not None:
            outcomes.append(
                (metric, _duration_seconds(match.group("value"), match.group("unit")))
            )
    for match in re.finditer(rf"(?P<value>{_NUMBER})\s*[x×]\s+faster\b", plain, re.I):
        outcomes.append(("speedup", _parse_number(match.group("value"))))
    throughput = re.search(
        rf"\b(?:peak\s+)?throughput\b[^:\n]*:\s*(?:>|~|≈)?\s*"
        rf"(?P<value>{_NUMBER})\s*(?P<scale>[kKmMgG]?)\s*"
        r"(?:msg(?:s)?|ops?|files?|records?|rows?)\s*/\s*s(?:ec(?:ond)?s?)?\b",
        plain,
        re.I,
    )
    if throughput is None and "throughput" in nearby.casefold():
        throughput = re.search(
            rf"\b(?:maintains?|sustains?|reaches?)\b[^\n]*?(?:>|~|≈)?\s*"
            rf"(?P<value>{_NUMBER})\s*(?P<scale>[kKmMgG]?)\s*"
            r"(?:msg(?:s)?|ops?|files?|records?|rows?)\s*/\s*s(?:ec(?:ond)?s?)?\b",
            plain,
            re.I,
        )
    if throughput is not None:
        scale = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0, "g": 1_000_000_000.0}[
            throughput.group("scale").casefold()
        ]
        outcomes.append(("throughput_ops_per_second", _parse_number(throughput.group("value")) * scale))
    return outcomes


def _extract_portable_result_claims(text: str) -> list[Claim]:
    """Parse common result formats using only stable, evidence-matchable metrics."""
    lines = text.splitlines()
    claims: list[Claim] = []
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if not headers or not separators or not _is_separator_row(separators, headers):
            index += 1
            continue
        metrics = [_portable_header_metric(header) for header in headers]
        row = index + 2
        while row < len(lines):
            cells = _split_table_row(lines[row])
            if not cells or len(cells) != len(headers):
                break
            row_metric_index = next(
                (
                    column
                    for column in range(min(2, len(cells)))
                    if _portable_row_metric(cells[column], cells[column + 1 :]) is not None
                ),
                None,
            )
            row_metric = None
            if row_metric_index is not None:
                row_metric = _portable_row_metric(
                    cells[row_metric_index], cells[row_metric_index + 1 :]
                )
            if (
                row_metric_index is not None
                and row_metric is not None
                and sum(metric is not None for metric in metrics[1:]) == 0
            ):
                for column in _portable_outcome_columns(headers, row_metric_index + 1):
                    for metric, value in _portable_cell_values(
                        row_metric, cells[row_metric_index], cells[column]
                    ):
                        claims.append(Claim(metric, value, lines[row], row + 1))
            else:
                for column, metric in enumerate(metrics):
                    if metric is None:
                        if re.search(
                            r"\bspeed\b", _plain_cell(headers[column]), re.I
                        ) and re.search(r"\bFPS\b", _plain_cell(cells[column]), re.I):
                            values = list(_NUMBER_RE.finditer(_plain_cell(cells[column])))
                            if values:
                                claims.append(
                                    Claim(
                                        "frames_per_second",
                                        _parse_number(values[0].group("value")),
                                        lines[row],
                                        row + 1,
                                    )
                                )
                        continue
                    for resolved_metric, value in _portable_cell_values(
                        metric, headers[column], cells[column]
                    ):
                        claims.append(Claim(resolved_metric, value, lines[row], row + 1))
            row += 1
        index = max(index + 1, row)
    for line_number, raw in enumerate(lines, start=1):
        plain = _plain_cell(raw)
        nearby = " ".join(
            _plain_cell(value) for value in lines[max(0, line_number - 26) : line_number - 1]
        )
        for metric, value in _portable_inline_outcomes(plain, nearby):
            claims.append(Claim(metric, value, raw, line_number))
        fps = re.search(rf"(?P<value>{_NUMBER})\s*(?P<scale>[kKmM]?)\s*FPS\b", plain, re.I)
        if fps is not None:
            claims.append(
                Claim(
                    "frames_per_second",
                    _scaled_result_number(f"{fps.group('value')}{fps.group('scale')}"),
                    raw,
                    line_number,
                )
            )
        tokens = re.search(
            rf"(?P<value>{_NUMBER})\s*(?:tokens?|tok)\s*/\s*s(?:ec(?:ond)?)?\b",
            plain,
            re.I,
        )
        if tokens is not None:
            claims.append(
                Claim("tokens_per_second", _parse_number(tokens.group("value")), raw, line_number)
            )
        console = {
            "user_time_seconds": r"User time \(seconds\):",
            "system_time_seconds": r"System time \(seconds\):",
            "cpu_percent": r"Percent of CPU this job got:",
            "memory_kb": r"Maximum resident set size \(kbytes\):",
        }
        for metric, prefix in console.items():
            match = re.search(rf"{prefix}\s*(?P<value>{_NUMBER})\s*%?", plain, re.I)
            if match is not None:
                claims.append(Claim(metric, _parse_number(match.group("value")), raw, line_number))
        elapsed = re.search(
            r"Elapsed \(wall clock\) time .*?:\s*(?P<minutes>\d+):(?P<seconds>\d+(?:\.\d+)?)",
            plain,
            re.I,
        )
        if elapsed is not None:
            value = float(elapsed.group("minutes")) * 60 + float(elapsed.group("seconds"))
            claims.append(Claim("elapsed_time_seconds", value, raw, line_number))
    return claims


def _extended_metric_from_header(header: str) -> str | None:
    plain = _plain_cell(header).casefold()
    compact = re.sub(r"[^a-z0-9@²$]+", " ", plain).strip()
    if "vectors/sec" in plain or "vectors per second" in plain:
        return "vectors_per_second"
    ranked = re.search(r"\b(?P<family>map|hits?)\s*@\s*(?P<cutoff>0?\.\d+|[1-9]\d*)\b", plain)
    if ranked is not None:
        family = "hits" if ranked.group("family").startswith("hit") else "map"
        cutoff = ranked.group("cutoff")
        normalized = (
            str(round(float(cutoff) * 100))
            if cutoff.startswith(".") or cutoff.startswith("0.")
            else cutoff
        )
        return f"{family}{normalized}"
    metric = _metric_from_header(header)
    if metric is not None:
        return metric
    exact = {
        "time s": "runtime_seconds",
        "time": "runtime_seconds",
        "loss": "loss",
        "val loss": "val_loss",
        "validation loss": "val_loss",
        "val accuracy": "val_accuracy",
        "validation accuracy": "val_accuracy",
        "req s": "requests_per_second",
        "rfid": "rfid",
        "gfid": "gfid",
        "zs acc": "zero_shot_accuracy",
        "lp acc": "linear_probe_accuracy",
        "decisions s": "decisions_per_second",
        "decisions hour": "decisions_per_hour",
        "$ 1k dec": "cost_per_1000_decisions",
        "vs monolith": "speedup",
    }
    if compact in exact:
        return exact[compact]
    if re.search(r"(?:时间|time).*\bs\b", plain):
        return "runtime_seconds"
    if "decisions/s" in plain:
        return "decisions_per_second"
    if "decisions/hour" in plain:
        return "decisions_per_hour"
    if "$/1k" in plain:
        return "cost_per_1000_decisions"
    return None


def _extended_table_values(metric: str, header: str, cell: str) -> list[float]:
    plain = _plain_cell(cell)
    if not plain or plain in {"—", "-", "Baseline", "baseline"}:
        return []
    if metric.endswith("_seconds"):
        unit = None
        unit_match = re.search(r"\b(us|µs|ms|s)\b", plain, re.I)
        if unit_match is not None:
            unit = unit_match.group(1)
        else:
            header_match = re.search(r"(?:\(|\b)(us|µs|ms|s)(?:\)|\b)", header, re.I)
            if header_match is not None:
                unit = header_match.group(1)
        values = [_parse_number(match.group("value")) for match in _NUMBER_RE.finditer(plain)]
        if unit is None:
            return []
        return [_duration_seconds(str(value), unit) for value in values]
    values = [_parse_number(match.group("value")) for match in _NUMBER_RE.finditer(plain)]
    if not values:
        return []
    percent = "%" in plain
    return [_normalize_value(metric, value, percent=percent) for value in values]


def _extract_extended_markdown_tables(lines: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if not headers or not separators or not _is_separator_row(separators, headers):
            index += 1
            continue
        metrics = [_extended_metric_from_header(header) for header in headers]
        compound = [_compound_metrics_from_header(header) for header in headers]
        row = index + 2
        if row < len(lines):
            lower = _split_table_row(lines[row])
            if (
                lower
                and len(lower) == len(headers)
                and all(
                    not _plain_cell(cell) or _extended_metric_from_header(cell) is not None
                    for cell in lower
                )
            ):
                lower_metrics = [_extended_metric_from_header(cell) for cell in lower]
                if sum(metric is not None for metric in lower_metrics) >= 2:
                    metrics = lower_metrics
                    row += 1
        while row < len(lines):
            cells = _split_table_row(lines[row])
            if not cells or len(cells) != len(headers):
                break
            row_metric = _extended_metric_from_header(cells[0])
            if row_metric is not None and sum(metric is not None for metric in metrics[1:]) == 0:
                for cell in cells[1:]:
                    for value in _extended_table_values(row_metric, headers[0], cell):
                        claims.append(Claim(row_metric, value, lines[row], row + 1))
            else:
                for column, metric in enumerate(metrics):
                    if metric is None:
                        continue
                    if compound[column]:
                        continue
                    for value in _extended_table_values(metric, headers[column], cells[column]):
                        claims.append(Claim(metric, value, lines[row], row + 1))
                for cell in cells:
                    if "slower" not in _plain_cell(cell).casefold():
                        continue
                    match = re.search(rf"(?P<value>{_NUMBER})\s*x", _plain_cell(cell), re.I)
                    if match is not None:
                        claims.append(
                            Claim(
                                "slowdown", _parse_number(match.group("value")), lines[row], row + 1
                            )
                        )
            row += 1
        index = max(row, index + 1)
    return claims


def _extract_embedded_delimited_tables(lines: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    for index, raw in enumerate(lines):
        if "\t" not in raw:
            continue
        headers = [cell.strip() for cell in raw.split("\t")]
        metrics = [_extended_metric_from_header(header) for header in headers]
        if sum(metric is not None for metric in metrics) < 2:
            continue
        row = index + 1
        while row < len(lines) and "\t" in lines[row]:
            cells = [cell.strip() for cell in lines[row].split("\t")]
            if len(cells) != len(headers):
                break
            for column, metric in enumerate(metrics):
                if metric is None:
                    continue
                for value in _extended_table_values(metric, headers[column], cells[column]):
                    claims.append(Claim(metric, value, lines[row], row + 1))
            row += 1
    return claims


def _scaled_result_number(raw: str) -> float:
    match = re.fullmatch(rf"\s*(?P<value>{_NUMBER})\s*(?P<scale>[kKmM]?)\s*", raw)
    if match is None:
        raise ValueError(raw)
    factor = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0}[match.group("scale").casefold()]
    return _parse_number(match.group("value")) * factor


def _extract_extended_console_claims(lines: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    for line_number, raw in enumerate(lines, start=1):
        plain = _plain_cell(raw)
        lower = plain.casefold()
        for match in re.finditer(
            rf"(?P<rate>[\d,]+(?:\.\d+)?)\s*ops/sec\b[^\n]*?\((?P<speed>{_NUMBER})x\)",
            plain,
            re.I,
        ):
            claims.extend(
                [
                    Claim(
                        "throughput_ops_per_second",
                        float(match.group("rate").replace(",", "")),
                        raw,
                        line_number,
                    ),
                    Claim("speedup", _parse_number(match.group("speed")), raw, line_number),
                ]
            )
        loaded = re.search(
            rf"Loaded\s+(?P<count>[\d,]+)\s+[^.]*?in\s+(?P<seconds>{_NUMBER})\s+seconds?\.\s*Data size is\s+(?P<size>{_NUMBER})K",
            plain,
            re.I,
        )
        if loaded is not None:
            claims.extend(
                [
                    Claim("record_count", _parse_number(loaded.group("count")), raw, line_number),
                    Claim(
                        "runtime_seconds", _parse_number(loaded.group("seconds")), raw, line_number
                    ),
                    Claim("data_size_kb", _parse_number(loaded.group("size")), raw, line_number),
                ]
            )
        insert = re.search(r"\bINSERT:\s*(?P<count>\d+)\s+rows?", plain, re.I)
        if insert is not None:
            claims.append(
                Claim("inserted_row_count", float(insert.group("count")), raw, line_number)
            )
        query = re.search(r"\bFINISHED,\s*(?P<count>\d+)\s+nodes?", plain, re.I)
        if query is not None:
            claims.append(Claim("node_count", float(query.group("count")), raw, line_number))
        splits = re.search(
            rf"Splits:\s*(?P<total>\d+)\s+total,\s*(?P<done>\d+)\s+done\s*\((?P<ratio>{_NUMBER})%\)",
            plain,
            re.I,
        )
        if splits is not None:
            claims.extend(
                [
                    Claim("total_split_count", float(splits.group("total")), raw, line_number),
                    Claim("completed_split_count", float(splits.group("done")), raw, line_number),
                    Claim(
                        "completion_ratio",
                        _parse_number(splits.group("ratio")) / 100,
                        raw,
                        line_number,
                    ),
                ]
            )
        presto = re.search(
            rf"(?P<minutes>\d+):(?P<seconds>\d{{2}})\s+\[(?P<rows>[\d,]+)\s+rows?,\s*(?P<bytes>{_NUMBER})(?P<byte_unit>[KMG]?B)\]\s+\[(?P<rate>{_NUMBER})\s+rows/s,\s*(?P<byte_rate>{_NUMBER})(?P<rate_unit>[KMG]?B)/s\]",
            plain,
            re.I,
        )
        if presto is not None:
            byte_scale = {"b": 1, "kb": 1_000, "mb": 1_000_000, "gb": 1_000_000_000}
            claims.extend(
                [
                    Claim(
                        "runtime_seconds",
                        float(presto.group("minutes")) * 60 + float(presto.group("seconds")),
                        raw,
                        line_number,
                    ),
                    Claim(
                        "returned_row_count", _parse_number(presto.group("rows")), raw, line_number
                    ),
                    Claim(
                        "data_read_bytes",
                        _parse_number(presto.group("bytes"))
                        * byte_scale[presto.group("byte_unit").casefold()],
                        raw,
                        line_number,
                    ),
                    Claim("rows_per_second", _parse_number(presto.group("rate")), raw, line_number),
                    Claim(
                        "bytes_per_second",
                        _parse_number(presto.group("byte_rate"))
                        * byte_scale[presto.group("rate_unit").casefold()],
                        raw,
                        line_number,
                    ),
                ]
            )
        keras: list[tuple[str, str]] = []
        if "ms/step" in plain or "val_" in lower or ("loss:" in lower and "accuracy:" in lower):
            keras = re.findall(
                rf"(?<![\w])(?P<metric>val_accuracy|val_loss|accuracy|loss):\s*(?P<value>{_NUMBER})",
                plain,
                re.I,
            )
        for metric, value in keras:
            normalized = {
                "val_loss": "validation_loss",
                "val_accuracy": "validation_accuracy",
            }.get(metric.casefold(), metric.casefold())
            claims.append(Claim(normalized, _parse_number(value), raw, line_number))
        progress = re.search(
            rf"-\s*(?P<seconds>{_NUMBER})s\s+(?P<step>{_NUMBER})ms/step", plain, re.I
        )
        if progress is not None:
            claims.extend(
                [
                    Claim(
                        "runtime_seconds",
                        _parse_number(progress.group("seconds")),
                        raw,
                        line_number,
                    ),
                    Claim(
                        "step_latency_seconds",
                        _parse_number(progress.group("step")) / 1000,
                        raw,
                        line_number,
                    ),
                ]
            )
        point_time = re.search(rf"[\d,]+\s+points:\s*(?P<value>{_NUMBER})\s*ms", plain, re.I)
        if point_time is not None:
            claims.append(
                Claim(
                    "runtime_seconds",
                    _parse_number(point_time.group("value")) / 1000,
                    raw,
                    line_number,
                )
            )
        best = re.search(
            rf"test\s+hits@(?P<hk>\d+)\s*=\s*(?P<hits>{_NUMBER}).*?epoch\s*=\s*(?P<epoch>\d+)",
            plain,
            re.I,
        )
        if best is not None:
            claims.extend(
                [
                    Claim(
                        f"hits_{best.group('hk')}",
                        _parse_number(best.group("hits")),
                        raw,
                        line_number,
                    ),
                    Claim("best_epoch", float(best.group("epoch")), raw, line_number),
                ]
            )
        fuzz_row = _split_table_row(raw)
        if fuzz_row and len(fuzz_row) >= 3:
            label = _plain_cell(fuzz_row[0]).casefold()
            metric = {
                "total execs (avg)": "total_execution_count",
                "total paths": "total_path_count",
                "total crashes": "total_crash_count",
            }.get(label)
            if metric is not None:
                for cell in fuzz_row[1:]:
                    first = re.search(
                        rf"(?P<value>{_NUMBER})\s*(?P<scale>[kKmM]?)", _plain_cell(cell)
                    )
                    if first is not None:
                        claims.append(
                            Claim(metric, _scaled_result_number(first.group(0)), raw, line_number)
                        )
                    if label == "total crashes":
                        unique = re.search(r"\((?P<value>\d+)\s+unique\)", _plain_cell(cell), re.I)
                        if unique is not None:
                            claims.append(
                                Claim(
                                    "unique_crash_count",
                                    float(unique.group("value")),
                                    raw,
                                    line_number,
                                )
                            )
        julia_range = re.search(
            rf"Range \(min .* max\):\s*(?P<min>{_NUMBER})\s*(?P<unit>ns|μs|µs|ms|s) .* (?P<max>{_NUMBER})\s*(?P=unit).*GC \(min .* max\):\s*(?P<gcmin>{_NUMBER})% .* (?P<gcmax>{_NUMBER})%",
            plain,
            re.I,
        )
        if julia_range is not None:
            unit = julia_range.group("unit").replace("μ", "µ")
            if unit == "ns":
                factor = 1e-9
            else:
                factor = {"µs": 1e-6, "ms": 1e-3, "s": 1}[unit]
            claims.extend(
                [
                    Claim(
                        "min_latency_seconds",
                        _parse_number(julia_range.group("min")) * factor,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "max_latency_seconds",
                        _parse_number(julia_range.group("max")) * factor,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "gc_min_ratio",
                        _parse_number(julia_range.group("gcmin")) / 100,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "gc_max_ratio",
                        _parse_number(julia_range.group("gcmax")) / 100,
                        raw,
                        line_number,
                    ),
                ]
            )
        julia_median = re.search(
            rf"Time\s+\(median\):\s*(?P<value>{_NUMBER})\s*(?P<unit>ns|μs|µs|ms|s).*GC \(median\):\s*(?P<gc>{_NUMBER})%",
            plain,
            re.I,
        )
        if julia_median is not None:
            unit = julia_median.group("unit").replace("μ", "µ")
            factor = {"ns": 1e-9, "µs": 1e-6, "ms": 1e-3, "s": 1}[unit]
            claims.extend(
                [
                    Claim(
                        "median_latency_seconds",
                        _parse_number(julia_median.group("value")) * factor,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "gc_median_ratio",
                        _parse_number(julia_median.group("gc")) / 100,
                        raw,
                        line_number,
                    ),
                ]
            )
        julia_mean = re.search(
            rf"Time\s+\(mean .*\):\s*(?P<mean>{_NUMBER})\s*(?P<unit>ns|μs|µs|ms|s) .* (?P<sd>{_NUMBER})\s*(?P=unit).*GC \(mean .*\):\s*(?P<gcmean>{_NUMBER})% .* (?P<gcsd>{_NUMBER})%",
            plain,
            re.I,
        )
        if julia_mean is not None:
            unit = julia_mean.group("unit").replace("μ", "µ")
            factor = {"ns": 1e-9, "µs": 1e-6, "ms": 1e-3, "s": 1}[unit]
            claims.extend(
                [
                    Claim(
                        "avg_latency_seconds",
                        _parse_number(julia_mean.group("mean")) * factor,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "latency_stdev_seconds",
                        _parse_number(julia_mean.group("sd")) * factor,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "gc_mean_ratio",
                        _parse_number(julia_mean.group("gcmean")) / 100,
                        raw,
                        line_number,
                    ),
                    Claim(
                        "gc_stdev_ratio",
                        _parse_number(julia_mean.group("gcsd")) / 100,
                        raw,
                        line_number,
                    ),
                ]
            )
    return claims


def _extract_extended_result_prose(lines: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    for line_number, raw in enumerate(lines, start=1):
        plain = _plain_cell(raw)
        lower = plain.casefold()
        previous = _plain_cell(lines[line_number - 2]).casefold() if line_number > 1 else ""
        for match in re.finditer(
            rf"(?P<low>{_NUMBER})\s*[–—-]\s*(?P<high>{_NUMBER})\s*[x×]", plain, re.I
        ):
            if "throughput" in lower or "what awareness" in lower:
                claims.append(Claim("speedup", _parse_number(match.group("low")), raw, line_number))
        for match in re.finditer(rf"(?P<value>{_NUMBER})\s*[x×]", plain, re.I):
            prefix = lower[max(0, match.start() - 18) : match.start()]
            metric = "memory_reduction" if "memory" in prefix else "speedup"
            if any(
                token in lower
                for token in (
                    "throughput",
                    "vectorized",
                    "cached duckdb",
                    "memory (",
                    "what awareness",
                )
            ):
                claims.append(Claim(metric, _parse_number(match.group("value")), raw, line_number))
        if any(
            token in lower
            for token in (
                "what awareness",
                "we improved",
                "compression ratio",
                "optimized for fast execution",
            )
        ):
            for match in re.finditer(
                rf"(?:ratio of|cr of|provides a cr of|gives a cr of|cr)\s*~?(?P<value>{_NUMBER})",
                plain,
                re.I,
            ):
                claims.append(
                    Claim(
                        "compression_ratio", _parse_number(match.group("value")), raw, line_number
                    )
                )
            for match in re.finditer(rf"~?(?P<value>{_NUMBER})\s*mb/s", plain, re.I):
                claims.append(
                    Claim(
                        "compression_throughput_mb_per_second",
                        _parse_number(match.group("value")),
                        raw,
                        line_number,
                    )
                )
        recall_comparison = any(
            token in f"{previous} {lower}" for token in ("near-dup recall/f1", "end-to-end recall")
        )
        if recall_comparison:
            for match in re.finditer(rf"~?(?P<value>{_NUMBER})\s*%", plain):
                claims.append(
                    Claim("recall", _parse_number(match.group("value")) / 100, raw, line_number)
                )
            for match in re.finditer(r"(?P<value>0\.\d+)", plain):
                claims.append(Claim("f1", _parse_number(match.group("value")), raw, line_number))
        if "precision" in lower and re.search(r"precision\s*\(", plain, re.I):
            for match in re.finditer(
                rf"precision\s*\([^\d]{{0,4}}(?P<value>{_NUMBER})", plain, re.I
            ):
                claims.append(
                    Claim("precision", _parse_number(match.group("value")), raw, line_number)
                )
        for match in re.finditer(
            rf"\b(?P<metric>F1|ROC-AUC)\s*`?(?P<value>{_NUMBER})", plain, re.I
        ):
            metric = "f1" if match.group("metric").casefold() == "f1" else "auroc"
            claims.append(Claim(metric, _parse_number(match.group("value")), raw, line_number))
        gpu = re.search(
            rf"up to\s+(?P<rate>{_NUMBER})\s+mini-batch per second.*?(?P<gpu>{_NUMBER})% of the time on the GPU \((?P<cpu>{_NUMBER})% on CPU and (?P<transfer>{_NUMBER})% moving data",
            plain,
            re.I,
        )
        if gpu is not None:
            claims.extend(
                [
                    Claim(
                        "minibatches_per_second", _parse_number(gpu.group("rate")), raw, line_number
                    ),
                    Claim(
                        "gpu_time_ratio", _parse_number(gpu.group("gpu")) / 100, raw, line_number
                    ),
                    Claim(
                        "cpu_time_ratio", _parse_number(gpu.group("cpu")) / 100, raw, line_number
                    ),
                    Claim(
                        "transfer_time_ratio",
                        _parse_number(gpu.group("transfer")) / 100,
                        raw,
                        line_number,
                    ),
                ]
            )
        sub_latency = re.search(rf"sub-\s*(?P<value>{_NUMBER})\s*ms\s+latency", plain, re.I)
        if sub_latency is not None:
            claims.append(
                Claim(
                    "runtime_seconds",
                    abs(_parse_number(sub_latency.group("value"))) / 1000,
                    raw,
                    line_number,
                )
            )
        rules = re.search(r"(?P<count>\d+)\s+rules\b", plain, re.I)
        if rules is not None and "latency" in lower:
            claims.append(Claim("rule_count", float(rules.group("count")), raw, line_number))
    return claims


def _markdown_table_header_lines(lines: list[str]) -> set[int]:
    header_lines: set[int] = set()
    for index in range(len(lines) - 1):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if headers and separators and _is_separator_row(separators, headers):
            header_lines.update({index + 1, index + 2})
            lower = _split_table_row(lines[index + 2]) if index + 2 < len(lines) else None
            if (
                lower
                and len(lower) == len(headers)
                and not any(_NUMBER_RE.search(_plain_cell(cell)) for cell in lower)
            ):
                header_lines.add(index + 3)
    return header_lines


def _delimited_table_header_lines(lines: list[str]) -> set[int]:
    header_lines: set[int] = set()
    for index, line in enumerate(lines):
        if "\t" not in line:
            continue
        cells = [cell.strip() for cell in line.split("\t")]
        if sum(_extended_metric_from_header(cell) is not None for cell in cells) >= 2:
            header_lines.add(index + 1)
    return header_lines


def _suppressed_benchmark_claims(text: str) -> set[tuple[int, str, float]]:
    """Suppress target/threshold columns when a table reports achieved outcomes separately."""
    suppressed: set[tuple[int, str, float]] = set()
    lines = text.splitlines()
    for index in range(len(lines) - 2):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if not headers or not separators or not _is_separator_row(separators, headers):
            continue
        normalized = [_plain_cell(header).casefold() for header in headers]
        excluded_columns = [
            column
            for column, header in enumerate(normalized)
            if any(
                word in header
                for word in (
                    "expected",
                    "target",
                    "threshold",
                    "goal",
                    "claimed",
                    "status",
                    "note",
                    "ratio",
                    "improvement",
                    "change",
                    "delta",
                    "gap",
                )
            )
        ]
        if excluded_columns:
            row = index + 2
            while row < len(lines):
                cells = _split_table_row(lines[row])
                if not cells or len(cells) != len(headers):
                    break
                row_metric = _extended_metric_from_header(cells[0])
                for column in excluded_columns:
                    metric = row_metric or _portable_header_metric(headers[column])
                    if metric is None:
                        metric = next(
                            (
                                _portable_header_metric(header)
                                for candidate, header in enumerate(headers)
                                if candidate != column
                                and _portable_header_metric(header) is not None
                                and "measured" in normalized[candidate]
                            ),
                            None,
                        )
                    if metric is None:
                        continue
                    for value in _extended_table_values(metric, headers[column], cells[column]):
                        suppressed.add((row + 1, metric, round(value, 12)))
                row += 1
        if (
            "threshold" not in normalized
            or "achieved" not in normalized
            or "metric" not in normalized
        ):
            continue
        metric_column = normalized.index("metric")
        threshold_column = normalized.index("threshold")
        row = index + 2
        while row < len(lines):
            cells = _split_table_row(lines[row])
            if not cells or len(cells) != len(headers):
                break
            metric = _extended_metric_from_header(cells[metric_column])
            if metric is not None:
                for value in _extended_table_values(
                    metric, headers[threshold_column], cells[threshold_column]
                ):
                    suppressed.add((row + 1, metric, round(value, 12)))
            row += 1
    return suppressed


def _extract_general_result_claims(text: str) -> list[Claim]:
    """Extract common result prose and console formats without repository-specific rules."""
    claims: list[Claim] = []
    raw_lines = text.splitlines()
    for line_number, raw_line in enumerate(raw_lines, start=1):
        line = _plain_cell(raw_line)
        for match in _THROUGHPUT_BOOST_RE.finditer(line):
            claims.append(
                Claim("speedup", _parse_number(match.group("value")), raw_line, line_number)
            )
        for match in _OPTIMAL_THROUGHPUT_RE.finditer(line):
            claims.append(
                Claim(
                    "optimal_throughput_ratio",
                    _parse_number(match.group("value")) / 100,
                    raw_line,
                    line_number,
                )
            )
        for match in _OPTIMAL_THROUGHPUT_RANGE_RE.finditer(line):
            for group in ("low", "high"):
                claims.append(
                    Claim(
                        "optimal_throughput_ratio",
                        _parse_number(match.group(group)) / 100,
                        raw_line,
                        line_number,
                    )
                )
        lower_line = line.casefold()
        if "improv" in lower_line or "decline" in lower_line:
            for match in _METRIC_IMPROVEMENT_RE.finditer(line):
                matched_phrase = match.group(0).casefold()
                direction = "decline" if "declin" in matched_phrase else "improvement"
                raw_metric = match.group("metric").casefold().replace(" ", "-")
                base = {
                    "aff-f1": "aff_f1",
                    "weighted-f1": "weighted_f1",
                    "rouge-l": "rouge_l",
                    "auc": "auc",
                }.get(raw_metric, canonical_metric(raw_metric))
                metric = f"{base}_{direction}"
                claims.append(
                    Claim(metric, _parse_number(match.group("value")) / 100, raw_line, line_number)
                )
            for match in _PERCENT_IN_METRIC_RE.finditer(line):
                prefix = line[max(0, match.start() - 100) : match.start()].casefold()
                direction = (
                    "decline" if prefix.rfind("declin") > prefix.rfind("improv") else "improvement"
                )
                base = canonical_metric(match.group("metric"))
                claims.append(
                    Claim(
                        f"{base}_{direction}",
                        _parse_number(match.group("value")) / 100,
                        raw_line,
                        line_number,
                    )
                )
        for match in _POSTFIX_METRIC_RE.finditer(line):
            metric = canonical_metric(match.group("metric"))
            claims.append(
                Claim(metric, _parse_number(match.group("value")) / 100, raw_line, line_number)
            )
        for match in _BEST_METRIC_RE.finditer(line):
            metric = canonical_metric(match.group("metric"))
            value = _normalize_value(
                metric,
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            claims.append(Claim(metric, value, raw_line, line_number))
        for match in _APPROXIMATE_METRIC_RE.finditer(raw_line):
            metric = canonical_metric(match.group("metric"))
            claims.append(
                Claim(metric, _parse_number(match.group("value")) / 100, raw_line, line_number)
            )
        fragmented = _FRAGMENTED_MEMORY_RE.search(line)
        if fragmented is not None:
            claims.extend(
                [
                    Claim(
                        "memory_mb",
                        _memory_mb(fragmented.group("memory"), fragmented.group("unit")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "fragmentation_ratio",
                        _parse_number(fragmented.group("ratio")) / 100,
                        raw_line,
                        line_number,
                    ),
                ]
            )
        fragmentation_bound = _FRAGMENTATION_BOUND_RE.search(line)
        if fragmentation_bound is not None:
            claims.append(
                Claim(
                    "fragmentation_ratio",
                    _parse_number(fragmentation_bound.group("value")) / 100,
                    raw_line,
                    line_number,
                )
            )
        artifact = _ARTIFACT_SIZE_RE.search(line)
        if artifact is not None:
            claims.append(
                Claim(
                    "artifact_size_mb",
                    _memory_mb(artifact.group("value"), artifact.group("unit")),
                    raw_line,
                    line_number,
                )
            )
        for regex, metric in ((_MAX_BATCH_RE, "max_batch_size"), (_OOM_BATCH_RE, "oom_batch_size")):
            match = regex.search(line)
            if match is not None:
                claims.append(
                    Claim(metric, _parse_number(match.group("value")), raw_line, line_number)
                )
        batch_speedup = _BATCH_SPEEDUP_RE.search(line)
        if batch_speedup is not None:
            claims.append(
                Claim("speedup", _parse_number(batch_speedup.group("value")), raw_line, line_number)
            )
        if re.search(r"\bpython\b", line, re.I):
            prior = " ".join(
                _plain_cell(value) for value in raw_lines[max(0, line_number - 6) : line_number - 1]
            )
            if re.search(r"maximum\s+batch\s+size|increase[^.]*batch\s+size", prior, re.I):
                command_number = re.search(
                    r"\bpython\b[^\n]*?\s(?P<value>[1-9]\d*)\s*$", line, re.I
                )
                if command_number is not None:
                    claims.append(
                        Claim(
                            "max_batch_size",
                            _parse_number(command_number.group("value")),
                            raw_line,
                            line_number,
                        )
                    )
        assertion = _ASSERTION_TEST_RE.search(line)
        if assertion is not None:
            claims.extend(
                [
                    Claim(
                        "assertion_count",
                        _parse_number(assertion.group("assertions")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "test_count", _parse_number(assertion.group("tests")), raw_line, line_number
                    ),
                ]
            )
        wrk_latency = _WRK_LATENCY_RE.search(line)
        if wrk_latency is not None:
            claims.extend(
                [
                    Claim(
                        "avg_latency_seconds",
                        _duration_seconds(wrk_latency.group("avg"), wrk_latency.group("unit")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "latency_stdev_seconds",
                        _duration_seconds(wrk_latency.group("stdev"), wrk_latency.group("unit")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "max_latency_seconds",
                        _duration_seconds(wrk_latency.group("max"), wrk_latency.group("unit")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "within_stdev_ratio",
                        _parse_number(wrk_latency.group("within")) / 100,
                        raw_line,
                        line_number,
                    ),
                ]
            )
        wrk_req = _WRK_REQ_RE.search(line)
        if wrk_req is not None:
            for group in ("avg", "stdev", "max"):
                scale = wrk_req.group(f"{group}_scale").casefold()
                value = (
                    _parse_number(wrk_req.group(group)) * {"": 1, "k": 1000, "m": 1_000_000}[scale]
                )
                claims.append(Claim("requests_per_second", value, raw_line, line_number))
            claims.append(
                Claim(
                    "within_stdev_ratio",
                    _parse_number(wrk_req.group("within")) / 100,
                    raw_line,
                    line_number,
                )
            )
        total = _WRK_TOTAL_RE.search(line)
        if total is not None:
            data_factor = {"kb": 1 / 1024, "mb": 1, "gb": 1024}[total.group("unit").casefold()]
            claims.extend(
                [
                    Claim(
                        "request_count",
                        _parse_number(total.group("requests")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "runtime_seconds",
                        _parse_number(total.group("seconds")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "data_read_mb",
                        _parse_number(total.group("data")) * data_factor,
                        raw_line,
                        line_number,
                    ),
                ]
            )
        request_rate = _REQUESTS_PER_SECOND_RE.search(line)
        if request_rate is not None:
            claims.append(
                Claim(
                    "requests_per_second",
                    _parse_number(request_rate.group("value")),
                    raw_line,
                    line_number,
                )
            )
        counts = _RESULT_COUNT_RE.search(line)
        if counts is not None:
            for group, metric in (
                ("processed", "processed_token_count"),
                ("phrases", "phrase_count"),
                ("found", "found_phrase_count"),
                ("correct", "correct_phrase_count"),
            ):
                claims.append(
                    Claim(metric, _parse_number(counts.group(group)), raw_line, line_number)
                )
        trailing = _TRAILING_FOUND_COUNT_RE.search(line)
        if trailing is not None:
            claims.append(
                Claim(
                    "found_phrase_count",
                    _parse_number(trailing.group("found")),
                    raw_line,
                    line_number,
                )
            )
        if re.search(r"\bprecision\b", line, re.I) and line.count("%") + line.count(r"\%") >= 2:
            for match in _PAREN_PERCENT_RE.finditer(line):
                claims.append(
                    Claim(
                        "precision",
                        _parse_number(match.group("value")) / 100,
                        raw_line,
                        line_number,
                    )
                )
        calibration = _CALIBRATION_RE.search(line)
        if calibration is not None:
            latency_unit = calibration.group("latency_unit").replace("usec", "us")
            interval_unit = calibration.group("interval_unit").replace("msec", "ms")
            claims.extend(
                [
                    Claim(
                        "avg_latency_seconds",
                        _duration_seconds(calibration.group("latency"), latency_unit),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "sampling_interval_seconds",
                        _duration_seconds(calibration.group("interval"), interval_unit),
                        raw_line,
                        line_number,
                    ),
                ]
            )
        paired_stdev = _PAIRED_STDEV_RE.search(line)
        if paired_stdev is not None:
            mentioned = []
            for token, metric in (("BLEU", "bleu_stdev"), ("ROUGE-L", "rouge_l_stdev")):
                if token.casefold() in line.casefold():
                    mentioned.append(metric)
            if len(mentioned) == 2:
                claims.extend(
                    [
                        Claim(
                            mentioned[0],
                            _parse_number(paired_stdev.group("first")),
                            raw_line,
                            line_number,
                        ),
                        Claim(
                            mentioned[1],
                            _parse_number(paired_stdev.group("second")),
                            raw_line,
                            line_number,
                        ),
                    ]
                )
    return claims


def _extract_generic_benchmark_claims(text: str) -> list[Claim]:
    """Parse reusable metric/value grammars used by benchmark prose and consoles."""
    claims: list[Claim] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        plain = _plain_cell(raw_line)
        lower = plain.casefold()

        if "accuracy" in lower and "this should" in lower:
            for match in re.finditer(rf"(?P<value>{_NUMBER})\s*%", plain, re.I):
                claims.append(
                    Claim(
                        "accuracy",
                        _parse_number(match.group("value")) / 100,
                        raw_line,
                        line_number,
                    )
                )
        for match in re.finditer(
            rf"(?P<value>{_NUMBER})\s*%\s+pass\s*@\s*(?P<k>[1-9]\d*)", plain, re.I
        ):
            claims.append(
                Claim(
                    f"pass_{match.group('k')}",
                    _parse_number(match.group("value")) / 100,
                    raw_line,
                    line_number,
                )
            )
        for match in re.finditer(
            rf"\b(?P<metric>PCC|MAE)\s+of\s+(?P<value>{_NUMBER})", plain, re.I
        ):
            claims.append(
                Claim(
                    canonical_metric(match.group("metric")),
                    _parse_number(match.group("value")),
                    raw_line,
                    line_number,
                )
            )
        if "perplexity" in lower and "/" in plain and "train an" in lower:
            result_part = re.split(r"\bperplexity\b", plain, maxsplit=1, flags=re.I)
            result_part = result_part[0] + " " + (result_part[1] if len(result_part) > 1 else "")
            for match in _NUMBER_RE.finditer(result_part):
                value = _parse_number(match.group("value"))
                if 10 <= value <= 1000:
                    claims.append(Claim("perplexity", value, raw_line, line_number))
        route_rate = re.search(r"(?P<value>[0-9][0-9,]*(?:\.[0-9]+)?)\s+req/sec\s*$", plain, re.I)
        if route_rate is not None:
            claims.append(
                Claim(
                    "requests_per_second",
                    float(route_rate.group("value").replace(",", "")),
                    raw_line,
                    line_number,
                )
            )
        jmh = re.search(rf"\b(?P<value>{_NUMBER})\s+(?P<unit>ops/s|ns/op)\s*$", plain, re.I)
        if jmh is not None:
            value = _parse_number(jmh.group("value"))
            metric = "throughput_ops_per_second"
            if jmh.group("unit").casefold() == "ns/op":
                metric = "avg_latency_seconds"
                value /= 1_000_000_000
            claims.append(Claim(metric, value, raw_line, line_number))
        position = re.search(
            rf"\bpositions:\s*(?P<count>{_NUMBER}),\s*positions per second:\s*(?P<rate>{_NUMBER})",
            plain,
            re.I,
        )
        if position is not None:
            claims.extend(
                [
                    Claim(
                        "position_count",
                        _parse_number(position.group("count")),
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "positions_per_second",
                        _parse_number(position.group("rate")),
                        raw_line,
                        line_number,
                    ),
                ]
            )
        dns_patterns = (
            (
                r"Total requests:\s*(?P<a>\d+)\s+of\s+(?P<b>\d+)\s+\((?P<c>[\d.]+)%\)",
                (
                    ("total_request_count", "a", 1),
                    ("completed_request_count", "b", 1),
                    ("completion_ratio", "c", 0.01),
                ),
            ),
            (r"DNS success codes:\s*(?P<a>\d+)", (("dns_success_count", "a", 1),)),
            (r"NOERROR:\s*(?P<a>\d+)", (("noerror_count", "a", 1),)),
            (
                rf"Time taken for tests:\s*(?P<a>{_NUMBER})(?P<unit>us|µs|ms|s)",
                (("runtime_seconds", "a", "duration"),),
            ),
            (rf"Questions per second:\s*(?P<a>{_NUMBER})", (("questions_per_second", "a", 1),)),
            (r"DNS timings,\s*(?P<a>\d+)\s+datapoints", (("datapoint_count", "a", 1),)),
        )
        for pattern, outputs in dns_patterns:
            match = re.search(pattern, plain, re.I)
            if match is None:
                continue
            for metric, group, factor in outputs:
                if factor == "duration":
                    value = _duration_seconds(match.group(group), match.group("unit"))
                else:
                    assert not isinstance(factor, str)
                    value = _parse_number(match.group(group)) * factor
                claims.append(Claim(metric, value, raw_line, line_number))
        timing = re.search(
            rf"^(?P<label>min|mean|\[\+/-sd\]|max):\s*(?P<value>{_NUMBER})(?P<unit>us|µs|ms|s)$",
            plain,
            re.I,
        )
        if timing is not None:
            metric = {
                "min": "min_latency_seconds",
                "mean": "avg_latency_seconds",
                "[+/-sd]": "latency_stdev_seconds",
                "max": "max_latency_seconds",
            }[timing.group("label").casefold()]
            claims.append(
                Claim(
                    metric,
                    _duration_seconds(timing.group("value"), timing.group("unit")),
                    raw_line,
                    line_number,
                )
            )
        for pattern, metric in (
            (
                rf"~?(?P<value>{_NUMBER})\s*(?:µs|us|µsec|usec|msec|ms)\s+delay",
                "channel_delay_seconds",
            ),
            (rf"updated in\s*<\s*(?P<value>{_NUMBER})\s*(?:µs|us)", "all_channel_update_seconds"),
            (
                rf"precision can be\s*<\s*(?P<value>{_NUMBER})\s*(?:µs|us)",
                "waveform_precision_seconds",
            ),
        ):
            match = re.search(pattern, plain, re.I)
            if match is not None:
                claims.append(
                    Claim(
                        metric,
                        _parse_number(match.group("value")) / 1_000_000,
                        raw_line,
                        line_number,
                    )
                )
        if "ripple" in lower:
            for match in re.finditer(rf"~?(?P<value>{_NUMBER})\s*mV", plain, re.I):
                claims.append(
                    Claim(
                        "ripple_volts",
                        _parse_number(match.group("value")) / 1000,
                        raw_line,
                        line_number,
                    )
                )
        compression = re.search(
            rf"compression ratio of\s+(?P<ratio>{_NUMBER})%\s*\(~?(?P<factor>{_NUMBER})x[^)]*\).*?~?(?P<accuracy>{_NUMBER})%\s+search accuracy",
            plain,
            re.I,
        )
        if compression is not None:
            claims.extend(
                [
                    Claim(
                        "compression_ratio",
                        _parse_number(compression.group("ratio")) / 100,
                        raw_line,
                        line_number,
                    ),
                    Claim(
                        "speedup", _parse_number(compression.group("factor")), raw_line, line_number
                    ),
                    Claim(
                        "search_accuracy",
                        _parse_number(compression.group("accuracy")) / 100,
                        raw_line,
                        line_number,
                    ),
                ]
            )
        if "flop" in lower:
            match = re.search(
                rf"(?P<value>{_NUMBER})\s+add-multiply operations\s*\(FLOPs\)", plain, re.I
            )
            if match is not None:
                claims.append(
                    Claim("flop_count", _parse_number(match.group("value")), raw_line, line_number)
                )
        if "average time" in lower:
            match = re.search(
                rf"average time is given by\s*(?P<value>{_NUMBER})\s+seconds", plain, re.I
            )
            if match is not None:
                claims.append(
                    Claim(
                        "runtime_seconds",
                        _parse_number(match.group("value")),
                        raw_line,
                        line_number,
                    )
                )
        if "categorical accuracy" in lower:
            match = re.search(rf"accuracy[^.]*?equals\s*(?P<value>{_NUMBER})", plain, re.I)
            if match is not None:
                claims.append(
                    Claim("accuracy", _parse_number(match.group("value")), raw_line, line_number)
                )
        improvement = re.search(
            rf"approximately\s+(?P<value>{_NUMBER})%\s+increase in throughput", plain, re.I
        )
        if improvement is not None:
            claims.append(
                Claim(
                    "throughput_improvement",
                    _parse_number(improvement.group("value")) / 100,
                    raw_line,
                    line_number,
                )
            )
    claims.extend(_extract_grid_table_claims(text.splitlines()))
    claims.extend(_extract_box_latency_claims(text.splitlines()))
    claims.extend(_extract_whitespace_table_claims(text.splitlines()))
    claims.extend(_extract_short_separator_metric_table(text.splitlines()))
    return claims


def _extract_grid_table_claims(lines: list[str]) -> list[Claim]:
    """Parse pipe tables whose separator uses reStructuredText-style plus signs."""
    claims: list[Claim] = []
    for index in range(len(lines) - 2):
        if "|" not in lines[index] or "+" not in lines[index + 1]:
            continue
        if not re.fullmatch(r"[+|:=\-\s]+", lines[index + 1]):
            continue
        headers = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        metrics = [_metric_from_header(header) for header in headers]
        if sum(metric is not None for metric in metrics) < 2:
            continue
        row = index + 2
        while row < len(lines):
            raw = lines[row]
            if re.fullmatch(r"[+|:=\-\s]+", raw):
                row += 1
                continue
            if "|" not in raw:
                break
            cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
            if len(cells) != len(headers):
                break
            for column, metric in enumerate(metrics):
                if metric is None:
                    continue
                value = _table_value_for_header(metric, headers[column], cells[column])
                if value is not None:
                    claims.append(Claim(metric, value, raw, row + 1))
            row += 1
    return claims


def _extract_box_latency_claims(lines: list[str]) -> list[Claim]:
    """Parse Unicode box-drawing latency summaries with statistic columns."""
    claims: list[Claim] = []
    headers: list[str] | None = None
    for line_number, raw in enumerate(lines, start=1):
        if not raw.lstrip().startswith("┃") and not raw.lstrip().startswith("│"):
            continue
        cells = [cell.strip() for cell in re.split(r"[┃│]", raw) if cell.strip()]
        if cells and cells[0].casefold() == "metric":
            headers = cells
            continue
        if headers is None or len(cells) != len(headers):
            continue
        label = cells[0].casefold()
        if "time" not in label and "latency" not in label:
            continue
        unit_factor = 0.001 if "(ms)" in label else 1.0
        for header, cell in zip(headers[1:], cells[1:], strict=True):
            match = _NUMBER_RE.fullmatch(cell.replace(",", ""))
            if match is None:
                continue
            metric = {
                "avg": "avg_latency_seconds",
                "min": "min_latency_seconds",
                "max": "max_latency_seconds",
                "p99": "p99_latency_seconds",
                "p90": "p90_latency_seconds",
                "p50": "p50_latency_seconds",
                "std": "latency_stdev_seconds",
            }.get(header.casefold())
            if metric is not None:
                claims.append(
                    Claim(
                        metric, _parse_number(match.group("value")) * unit_factor, raw, line_number
                    )
                )
    return claims


def _extract_whitespace_table_claims(lines: list[str]) -> list[Claim]:
    """Parse compact console tables with whitespace-delimited numeric columns."""
    claims: list[Claim] = []
    active = False
    for line_number, raw in enumerate(lines, start=1):
        plain = _plain_cell(raw)
        if re.fullmatch(r"num-workers\s+samples/sec\s+TFLOPs", plain, re.I):
            active = True
            continue
        if not active:
            continue
        match = re.fullmatch(rf"\d+\s+(?P<samples>{_NUMBER})\s+(?P<tflops>{_NUMBER})", plain)
        if match is None:
            active = False
            continue
        claims.extend(
            [
                Claim(
                    "samples_per_second",
                    _parse_number(match.group("samples")),
                    raw,
                    line_number,
                ),
                Claim("tflops", _parse_number(match.group("tflops")), raw, line_number),
            ]
        )
    return claims


def _extract_short_separator_metric_table(lines: list[str]) -> list[Claim]:
    """Accept compact two-dash tables only when explicit metric headers make them unambiguous."""
    claims: list[Claim] = []
    for index in range(len(lines) - 2):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if headers is None or separators is None or len(headers) != len(separators):
            continue
        if not all(re.fullmatch(r":?-{2}:?", cell.replace(" ", "")) for cell in separators):
            continue
        metrics = [_metric_from_header(header) for header in headers]
        explicit = {metric for metric in metrics if metric is not None}
        if not {"accuracy", "weighted_f1"}.issubset(explicit):
            continue
        row = index + 2
        while row < len(lines):
            cells = _split_table_row(lines[row])
            if cells is None or len(cells) != len(headers):
                break
            for column, metric in enumerate(metrics):
                if metric is None:
                    continue
                value = _table_value(metric, cells[column])
                if value is not None:
                    claims.append(Claim(metric, value, lines[row], row + 1))
            row += 1
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
    if canonical == "score":
        return None
    tokens = set(re.split(r"[_.-]+", canonical))
    if tokens & _PARAMETER_TOKENS:
        return None
    family = metric_family(canonical)
    if family is None:
        measurement_suffixes = ("_close", "_count", "_pct", "_score")
        return canonical if canonical.endswith(measurement_suffixes) else None
    return family if canonical == family else canonical


def _count_value(raw: str) -> float:
    words = {"single": 1.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0}
    normalized = raw.casefold()
    if normalized in words:
        return words[normalized]
    return _parse_number(raw)


def _extract_markdown_table_claims(lines: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separators = _split_table_row(lines[index + 1])
        if not headers or not separators or not _is_separator_row(separators, headers):
            index += 1
            continue
        metrics = [
            _metric_from_comparison_header(headers, column) or _metric_from_header(header)
            for column, header in enumerate(headers)
        ]
        nearby_metrics = _nearby_unit_table_metrics(lines, index, headers)
        if nearby_metrics is not None:
            metrics = nearby_metrics
        compound_metrics = [_compound_metrics_from_header(header) for header in headers]
        transposed_metric = _nearby_table_metric(lines, index, headers)
        row_index = index + 2
        value_headers = headers
        if row_index < len(lines):
            lower_headers = _split_table_row(lines[row_index])
            multilevel = _multilevel_table_metrics(headers, lower_headers or [])
            if multilevel is not None:
                metrics = multilevel
                value_headers = lower_headers or headers
                row_index += 1
        while row_index < len(lines):
            cells = _split_table_row(lines[row_index])
            if not cells:
                break
            context = _table_context(headers, metrics, cells)
            if "runtime_seconds" in metrics and context.get("system", "").casefold().endswith(
                " speed"
            ):
                context["system"] = context["system"][: -len(" speed")].strip()
            claims.extend(
                _row_labeled_metric_claims(headers, cells, lines[row_index].strip(), row_index + 1)
            )
            claims.extend(
                _row_labeled_compound_claims(
                    headers, cells, lines[row_index].strip(), row_index + 1
                )
            )
            claims.extend(
                _embedded_context_claims(headers, cells, lines[row_index].strip(), row_index + 1)
            )
            claims.extend(_embedded_text_claims(cells, lines[row_index].strip(), row_index + 1))
            claims.extend(
                _header_embedded_claims(headers, cells, lines[row_index].strip(), row_index + 1)
            )
            claims.extend(
                _transposed_metric_claims(
                    headers,
                    cells,
                    lines[row_index].strip(),
                    row_index + 1,
                    transposed_metric,
                )
            )
            claims.extend(
                _embedded_duration_table_claims(
                    headers, cells, lines[row_index].strip(), row_index + 1
                )
            )
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                value = _table_value_for_header(metric, value_headers[column], cells[column])
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
                    if metric == "avg_latency_seconds":
                        claims.append(
                            Claim(
                                metric="latency_score_seconds",
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


def _multilevel_table_metrics(
    upper_headers: list[str], lower_headers: list[str]
) -> list[str | None] | None:
    """Resolve a second Markdown header row such as dataset + metric."""
    if len(upper_headers) != len(lower_headers) or not lower_headers:
        return None
    if any(_NUMBER_RE.search(_plain_cell(cell)) for cell in lower_headers):
        return None
    lower_metrics = [_metric_from_header(cell) for cell in lower_headers]
    if sum(metric is not None for metric in lower_metrics) < 2:
        return None
    resolved: list[str | None] = []
    for upper, lower_metric in zip(upper_headers, lower_metrics, strict=True):
        if lower_metric is None:
            resolved.append(None)
            continue
        scope = re.sub(r"[^a-z0-9]+", "_", _plain_cell(upper).casefold()).strip("_")
        scope = re.sub(r"_st$", "", scope)
        resolved.append(f"{scope}_{lower_metric}" if scope else lower_metric)
    return resolved


def _nearby_unit_table_metrics(
    lines: list[str], table_index: int, headers: list[str]
) -> list[str | None] | None:
    """Infer a table-wide metric from an explicit nearby unit declaration."""
    prefix = _plain_cell(" ".join(lines[max(0, table_index - 6) : table_index])).casefold()
    if re.search(r"numbers? (?:are|is) fps|frames per second", prefix):
        return [None, *("frames_per_second" for _ in headers[1:])]
    return None


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
    value = re.sub(r"[`*~]", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _metric_from_header(header: str) -> str | None:
    plain = _plain_cell(header).casefold().replace("_", " ")
    compact = re.sub(r"[^\w²]+", " ", plain, flags=re.UNICODE).strip()
    ranked = re.search(
        r"\b(?P<family>map|mar|mrr|mndcg|ndcg|precision|recall|p|r)\s*@\s*"
        r"(?P<k>[1-9]\d*|1k)\b",
        plain,
    )
    if ranked:
        family = {"p": "precision", "r": "recall"}.get(
            ranked.group("family"), ranked.group("family")
        )
        k = "1000" if ranked.group("k") == "1k" else ranked.group("k")
        return f"{family}_{k}"
    waymo = re.search(r"\b(maph|map)\s*l([12])\b", compact)
    if waymo:
        return f"{waymo.group(1)}_l{waymo.group(2)}"
    if re.search(r"\b(?:m\s*)?ap\b", compact) and _is_size_specific_ap(compact.split()):
        return None
    if re.fullmatch(r"pq\s+(?:th|st)", compact):
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
    if re.search(r"\brecall\s+speed\b", compact):
        return "runtime_seconds"
    if compact in {"mean", "mean score"}:
        return "score"
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        if alias == "score" and compact not in {"score", "mean", "mean score"}:
            continue
        normalized_alias = re.sub(r"[^\w²]+", " ", alias.casefold(), flags=re.UNICODE).strip()
        if normalized_alias and re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", compact):
            return METRIC_ALIASES[alias]
    return None


def _metric_from_row_label(header: str, cell: str) -> str | None:
    normalized_header = re.sub(
        r"[^\w]+", " ", _plain_cell(header).casefold(), flags=re.UNICODE
    ).strip()
    label = html.unescape(cell).casefold().strip()
    label = re.sub(r"<[^>]+>", "", label)
    label = label.replace("`", "").replace("*", "").replace(" ", "_")
    if normalized_header in {"metric", "measure", "метрика"}:
        embedded = re.findall(r"\b[\w]+_(?:pct|count|score)\b", label)
        if embedded:
            return canonical_metric(embedded[-1])
        if label in {"test", "tests", "test_count"}:
            return "test_count"
        if "@" not in label:
            direct_metric = _metric_from_header(label)
            if direct_metric is not None:
                return direct_metric
    if label.startswith("success_rate"):
        return "success_rate"
    if label == "recall" or label == "authored_pairs_merged" or label.startswith("recall_—_"):
        return "recall"
    if normalized_header not in {"", "metric", "measure", "метрика"}:
        return None
    match = re.fullmatch(
        r"(?P<family>map|mar|mrr|mndcg|ndcg|precision|recall|u_ndcg|u_recall)"
        r"@(?P<k>[1-9]\d*)(?:_\(s\))?",
        label,
    )
    if match is not None:
        return canonical_metric(f"{match.group('family')}_{match.group('k')}")
    direct = {
        "mrr": "mrr",
        "success_rate": "success_rate",
        "partial_rate": "partial_rate",
        "fail_rate": "fail_rate",
        "correctness": "correctness",
        "answer_coverage": "answer_coverage",
        "mean_tool_calls": "mean_tool_calls",
        "mean_tokens": "mean_tokens",
        "mean_wall_time": "mean_wall_time_seconds",
        "avg_latency": "avg_latency_seconds",
        "avg_latency_(s)": "avg_latency_seconds",
        "p95_latency": "p95_latency_seconds",
        "p95_latency_(s)": "p95_latency_seconds",
    }
    return direct.get(label)


def _embedded_context_claims(
    headers: list[str], cells: list[str], raw_text: str, line: int
) -> list[Claim]:
    claims: list[Claim] = []
    for column, header in enumerate(headers):
        if column >= len(cells):
            continue
        normalized_header = re.sub(
            r"[^\w]+", " ", _plain_cell(header).casefold(), flags=re.UNICODE
        ).strip()
        if normalized_header not in {"tool", "model", "name"}:
            continue
        label = _plain_cell(cells[column])
        match = re.search(r"\b(?P<count>[1-9]\d*)\s*[- ]?feat(?:ure)?s?\b", label, re.I)
        if match is not None:
            claims.append(
                Claim(
                    metric="feature_count",
                    value=float(match.group("count")),
                    raw_text=raw_text,
                    line=line,
                    context={"model": label},
                )
            )
    return claims


def _embedded_text_claims(cells: list[str], raw_text: str, line: int) -> list[Claim]:
    claims: list[Claim] = []
    seen: set[tuple[str, float]] = set()
    for cell in cells:
        plain = _plain_cell(cell)
        for match in _TEST_COUNT_RE.finditer(plain):
            value = _parse_number(match.group("value"))
            if ("test_count", value) not in seen:
                seen.add(("test_count", value))
                context = (
                    {"scope": match.group("scope")} if match.group("scope") else {"scope": "total"}
                )
                claims.append(
                    Claim(
                        metric="test_count",
                        value=value,
                        raw_text=raw_text,
                        line=line,
                        context=context,
                    )
                )
        for match in _ARTIFACT_SIZE_COMPARISON_RE.finditer(plain):
            factor = {"kib": 1 / 1024, "mib": 1, "gib": 1024}[match.group("unit").casefold()]
            for group, system in (("first", "reported artifact"), ("second", "baseline artifact")):
                value = _parse_number(match.group(group)) * factor
                if ("artifact_size_mb", value) not in seen:
                    seen.add(("artifact_size_mb", value))
                    claims.append(
                        Claim(
                            metric="artifact_size_mb",
                            value=value,
                            raw_text=raw_text,
                            line=line,
                            context={"system": system},
                        )
                    )
        for match in _RANKED_PROSE_RE.finditer(plain):
            metric = f"{match.group('family').casefold()}_{match.group('k')}"
            value = _normalize_value(
                metric,
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            if (metric, value) not in seen:
                seen.add((metric, value))
                claims.append(Claim(metric=metric, value=value, raw_text=raw_text, line=line))
        for match in _RANKED_ARROW_RE.finditer(plain):
            metric = f"{match.group('family').casefold()}_{match.group('k')}"
            value = _normalize_value(
                metric,
                _parse_number(match.group("value")),
                percent=bool(match.group("percent")),
            )
            if (metric, value) not in seen:
                seen.add((metric, value))
                claims.append(Claim(metric=metric, value=value, raw_text=raw_text, line=line))
        for match in _SEPARABILITY_RE.finditer(plain):
            value = _parse_number(match.group("value"))
            if ("separability_delta", value) not in seen:
                seen.add(("separability_delta", value))
                claims.append(
                    Claim(metric="separability_delta", value=value, raw_text=raw_text, line=line)
                )
    return claims


def _header_embedded_claims(
    headers: list[str], cells: list[str], raw_text: str, line: int
) -> list[Claim]:
    """Extract compound values whose meaning is declared by the column header."""
    claims: list[Claim] = []
    for column, header in enumerate(headers):
        if column >= len(cells):
            continue
        normalized = _plain_cell(header).casefold()
        cell = _plain_cell(cells[column])
        if "no-target" in normalized or "no target" in normalized:
            match = re.search(rf"(?P<count>{_NUMBER})\s*\((?P<ratio>{_NUMBER})%\)", cell)
            if match is not None:
                claims.extend(
                    [
                        Claim(
                            "no_target_count", _parse_number(match.group("count")), raw_text, line
                        ),
                        Claim(
                            "no_target_ratio",
                            _parse_number(match.group("ratio")) / 100,
                            raw_text,
                            line,
                        ),
                    ]
                )
        if "main metric" in normalized:
            triple = re.search(
                rf"mAP\s+Full/Pres/Abs:\s*(?P<full>{_NUMBER})\s*/\s*"
                rf"(?P<present>{_NUMBER})\s*/\s*(?P<absent>{_NUMBER})",
                cell,
                re.I,
            )
            if triple is not None:
                for group, metric in (
                    ("full", "map_full"),
                    ("present", "map_present"),
                    ("absent", "map_absent"),
                ):
                    claims.append(
                        Claim(metric, _parse_number(triple.group(group)) / 100, raw_text, line)
                    )
            pair = re.search(
                rf"Pr\.\s*(?P<precision>{_NUMBER}),\s*N-acc\.\s*(?P<negative>{_NUMBER})",
                cell,
                re.I,
            )
            if pair is not None:
                claims.extend(
                    [
                        Claim(
                            "precision",
                            _parse_number(pair.group("precision")) / 100,
                            raw_text,
                            line,
                        ),
                        Claim(
                            "negative_accuracy",
                            _parse_number(pair.group("negative")) / 100,
                            raw_text,
                            line,
                        ),
                    ]
                )
        if "delta" in normalized or "Δ" in header:
            match = re.search(rf"(?P<value>[+-]?{_NUMBER})\s*(?:pp|%)", cell, re.I)
            if match is not None:
                base_metric = next(
                    (
                        metric
                        for prior in reversed(headers[:column])
                        if (metric := _metric_from_header(prior)) is not None
                    ),
                    None,
                )
                if base_metric is not None:
                    claims.append(
                        Claim(
                            f"{base_metric}_delta",
                            _parse_number(match.group("value")) / 100,
                            raw_text,
                            line,
                        )
                    )
    return claims


def _row_labeled_metric_claims(
    headers: list[str], cells: list[str], raw_text: str, line: int
) -> list[Claim]:
    if not headers or not cells:
        return []
    metric = _metric_from_row_label(headers[0], cells[0])
    if metric is None:
        return []
    claims: list[Claim] = []
    for column in range(1, min(len(headers), len(cells))):
        system = _plain_cell(headers[column])
        value = _table_value(metric, cells[column])
        numbers = list(_NUMBER_RE.finditer(_plain_cell(cells[column])))
        if value is None:
            value = _ratio_cell_value(metric, cells[column])
        if system.casefold() == "delta" and numbers and "pp" in _plain_cell(cells[column]):
            value = _parse_number(numbers[0].group("value")) / 100
        if value is None and system.casefold() == "delta" and numbers:
            value = _normalize_value(
                metric,
                _parse_number(numbers[0].group("value")),
                percent=bool(numbers[0].group("percent")) or "pp" in _plain_cell(cells[column]),
            )
        if value is None:
            continue
        context = {"system": system} if system else {}
        claims.append(
            Claim(metric=metric, value=value, raw_text=raw_text, line=line, context=context)
        )
        if system.casefold() == "delta":
            if len(numbers) >= 2:
                percent_value = _parse_number(numbers[1].group("value"))
                claims.append(
                    Claim(
                        metric=f"{metric}_delta_percent",
                        value=percent_value,
                        raw_text=raw_text,
                        line=line,
                        context=context,
                    )
                )
    return claims


def _row_labeled_compound_claims(
    headers: list[str], cells: list[str], raw_text: str, line: int
) -> list[Claim]:
    """Parse rows such as `accuracy / macro F1 | 87% / 86%`."""
    if len(headers) < 2 or len(cells) < 2:
        return []
    first_header = _plain_cell(headers[0]).casefold()
    if first_header not in {"metric", "measurement", "measure"}:
        return []
    label = _plain_cell(cells[0]).casefold()
    if "feature" in label and "check" in label:
        match = re.search(r"(?P<total>\d+)\s+of\s+(?P<exact>\d+)\s+exact", cells[1], re.I)
        if match is not None:
            return [
                Claim("feature_check_count", float(match.group("total")), raw_text, line),
                Claim("exact_feature_check_count", float(match.group("exact")), raw_text, line),
            ]
    if "flash" in label and "sram" in label:
        values = re.findall(rf"(?P<value>{_NUMBER})\s*B", _plain_cell(cells[1]), re.I)
        if len(values) == 2:
            return [
                Claim("flash_bytes", _parse_number(values[0]), raw_text, line),
                Claim("sram_bytes", _parse_number(values[1]), raw_text, line),
            ]
    if "/" not in cells[0]:
        return []
    metrics = [_metric_from_header(part) for part in _plain_cell(cells[0]).split("/")]
    values = [part.strip() for part in _plain_cell(cells[1]).split("/")]
    if len(metrics) != len(values) or any(metric is None for metric in metrics):
        return []
    claims: list[Claim] = []
    for metric, cell in zip(metrics, values, strict=True):
        assert metric is not None
        value = _table_value(metric, cell)
        if value is not None:
            claims.append(Claim(metric, value, raw_text, line))
    return claims


def _nearby_table_metric(lines: list[str], table_index: int, headers: list[str]) -> str | None:
    first = re.sub(r"[^\w]+", " ", _plain_cell(headers[0]).casefold(), flags=re.UNICODE).strip()
    if first not in {"scenario", "сценарій"}:
        return None
    prefix = " ".join(lines[max(0, table_index - 5) : table_index])
    match = re.search(
        r"(?<![\w])(?P<family>map|mar|mrr|mndcg|ndcg|precision|recall)\s*@\s*"
        r"(?P<k>[1-9]\d*)",
        _plain_cell(prefix),
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return f"{match.group('family').casefold()}_{match.group('k')}"


def _transposed_metric_claims(
    headers: list[str],
    cells: list[str],
    raw_text: str,
    line: int,
    metric: str | None,
) -> list[Claim]:
    if metric is None or not cells:
        return []
    scenario = _plain_cell(cells[0])
    claims: list[Claim] = []
    for column in range(1, min(len(headers), len(cells))):
        value = _table_value(metric, cells[column])
        if value is None:
            continue
        claims.append(
            Claim(
                metric=metric,
                value=value,
                raw_text=raw_text,
                line=line,
                context={"scenario": scenario, "system": _plain_cell(headers[column])},
            )
        )
    return claims


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
        value = _parse_number(match.group("value"))
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

    if re.search(r"\bmape\b", compact):
        return None
    is_map = bool(re.search(r"\bm\s*ap\b|\bmap(?!e\b)", compact))
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
        metrics = [
            _metric_from_comparison_header(headers, column) or _metric_from_header(header)
            for column, header in enumerate(headers)
        ]
        for cells, line in table[1:]:
            context = _table_context(headers, metrics, cells)
            claims.extend(_row_labeled_metric_claims(headers, cells, " | ".join(cells), line))
            claims.extend(_embedded_context_claims(headers, cells, " | ".join(cells), line))
            claims.extend(_embedded_text_claims(cells, " | ".join(cells), line))
            claims.extend(_header_embedded_claims(headers, cells, " | ".join(cells), line))
            claims.extend(_embedded_duration_table_claims(headers, cells, " | ".join(cells), line))
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                value = _table_value_for_header(metric, headers[column], cells[column])
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
                    if metric == "avg_latency_seconds":
                        claims.append(
                            Claim(
                                metric="latency_score_seconds",
                                value=value,
                                raw_text=" | ".join(cells),
                                line=line,
                                context=context,
                            )
                        )
    return claims


def _table_value(metric: str, cell: str) -> float | None:
    plain_cell = _plain_cell(cell)
    if re.fullmatch(r"[A-Za-z_]+\d+(?:[A-Za-z_]+)?", plain_cell):
        return None
    if metric.endswith("_seconds"):
        return _duration_cell_seconds(cell)
    if metric == "throughput_ops_per_second":
        scaled = _scaled_quantity(cell)
        if scaled is not None:
            return scaled
    if metric == "memory_mb":
        memory = re.fullmatch(rf"\s*(?P<value>{_NUMBER})\s*(?P<unit>kb|mb|gb)\s*", plain_cell, re.I)
        if memory is not None:
            return _memory_mb(memory.group("value"), memory.group("unit"))
    if metric in {"requests_per_second", "tokens_per_second_gpu"}:
        scaled = _scaled_quantity(cell)
        if scaled is not None:
            return scaled
    matches = list(_NUMBER_RE.finditer(plain_cell))
    if len(matches) != 1:
        return None
    match = matches[0]
    value = _parse_number(match.group("value"))
    return _normalize_value(metric, value, percent=bool(match.group("percent")))


def _table_value_for_header(metric: str, header: str, cell: str) -> float | None:
    """Parse a cell while honoring a unit declared once in its column header."""
    value = _table_value(metric, cell)
    if value is not None:
        plain_header = _plain_cell(header).casefold()
        if metric in {"artifact_size_kb", "artifact_size_mb"}:
            unit_match = re.search(r"\b(?P<unit>kb|mb|gb)\b", plain_header)
            if unit_match is not None:
                value_mb = _memory_mb(str(value), unit_match.group("unit"))
                return value_mb * 1024 if metric == "artifact_size_kb" else value_mb
        if metric.endswith("_seconds") and not re.search(
            rf"{_NUMBER}\s*(?:us|µs|ms|s|sec(?:ond)?s?)\b", _plain_cell(cell), re.I
        ):
            value = None
        else:
            return value
    plain_header = _plain_cell(header).casefold()
    plain_cell = _plain_cell(cell)
    match = _NUMBER_RE.fullmatch(plain_cell.replace(",", ""))
    if match is None:
        return None
    number = _parse_number(match.group("value"))
    if metric.endswith("_seconds"):
        if re.search(r"\b(?:microseconds?|us|µs)\b", plain_header):
            return number / 1_000_000
        if re.search(r"\b(?:milliseconds?|ms)\b", plain_header):
            return number / 1_000
        if re.search(r"\b(?:seconds?|secs?|s)\b", plain_header):
            return number
    if metric in {"artifact_size_kb", "artifact_size_mb"}:
        unit_match = re.search(r"\b(?P<unit>kb|mb|gb)\b", plain_header)
        if unit_match is not None:
            value_mb = _memory_mb(str(number), unit_match.group("unit"))
            return value_mb * 1024 if metric == "artifact_size_kb" else value_mb
    return _normalize_value(
        metric,
        number,
        percent=bool(match.group("percent")) or "%" in plain_header,
    )


def _metric_from_comparison_header(headers: list[str], column: int) -> str | None:
    if column == 0 or not headers:
        return None
    first = _plain_cell(headers[0]).casefold()
    current = _plain_cell(headers[column]).casefold()
    if first not in {"benchmark", "metric", "measure"}:
        return None
    if current in {"old", "new", "before", "after", "previous", "current", "result"}:
        return "score"
    return None


def _memory_mb(value: str, unit: str) -> float:
    number = _parse_number(value)
    factors = {"kb": 1 / 1024, "mb": 1, "gb": 1024}
    return number * factors[unit.casefold()]


def _ratio_cell_value(metric: str, cell: str) -> float | None:
    plain = _plain_cell(cell)
    leading_percent = re.match(rf"\s*(?P<value>{_NUMBER})\s*%", plain)
    if leading_percent is not None:
        return _parse_number(leading_percent.group("value")) / 100
    ratio = re.fullmatch(
        rf"\s*(?P<numerator>{_NUMBER})\s+(?:of|/)\s*(?P<denominator>{_NUMBER})\s*",
        plain,
        flags=re.IGNORECASE,
    )
    if ratio is None or not is_unit_interval_metric(metric):
        return None
    denominator = _parse_number(ratio.group("denominator"))
    if denominator <= 0:
        return None
    return _parse_number(ratio.group("numerator")) / denominator


def _scaled_quantity(cell: str) -> float | None:
    plain = _plain_cell(cell).replace(",", "")
    match = re.fullmatch(
        rf"\s*(?P<value>{_NUMBER})\s*(?P<scale>[kKmM])?\s*(?:ops?)?\s*(?:/\s*s|per\s+second)?\s*",
        plain,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    scale = (match.group("scale") or "").casefold()
    return _parse_number(match.group("value")) * {"": 1, "k": 1_000, "m": 1_000_000}[scale]


def _embedded_duration_table_claims(
    headers: list[str], cells: list[str], raw_text: str, line: int
) -> list[Claim]:
    if len(cells) < 2:
        return []
    system = re.split(r"\s*\(", _context_label(cells[0]), maxsplit=1)[0].strip()
    if system.casefold().endswith(" speed"):
        system = system[: -len(" speed")].strip()
    claims: list[Claim] = []
    for column in range(1, min(len(headers), len(cells))):
        if _metric_from_header(headers[column]) is not None:
            continue
        match = _UNIT_DURATION_RE.search(_plain_cell(cells[column]))
        if match is None:
            continue
        claims.append(
            Claim(
                metric="runtime_seconds",
                value=_duration_seconds(match.group("value"), match.group("unit")),
                raw_text=raw_text,
                line=line,
                context={
                    "system": system,
                    "implementation": _plain_cell(headers[column]).casefold(),
                },
            )
        )
        plain_cell = _plain_cell(cells[column])
        bytes_match = re.search(rf"(?:,|^)\s*(?P<value>{_NUMBER})\s*B\b", plain_cell, re.I)
        if bytes_match is not None:
            claims.append(
                Claim(
                    metric="memory_bytes",
                    value=_parse_number(bytes_match.group("value")),
                    raw_text=raw_text,
                    line=line,
                    context={"system": system},
                )
            )
        allocation_match = re.search(rf"(?:,|^)\s*(?P<value>{_NUMBER})\s*GC\b", plain_cell, re.I)
        if allocation_match is not None:
            claims.append(
                Claim(
                    metric="allocation_count",
                    value=_parse_number(allocation_match.group("value")),
                    raw_text=raw_text,
                    line=line,
                    context={"system": system},
                )
            )
    return claims


def _extract_tsv_claims(text: str) -> list[Claim]:
    lines = text.splitlines()
    if len(lines) < 2 or "\t" not in lines[0]:
        return []
    headers = [_plain_cell(cell) for cell in lines[0].split("\t")]
    if len(headers) < 2:
        return []
    metrics: list[str | None] = [None]
    for header in headers[1:]:
        canonical = canonical_metric(header)
        metrics.append(canonical if re.fullmatch(r"[a-z][a-z0-9_]*", canonical) else None)
    context_key = canonical_metric(headers[0]) or "item"
    claims: list[Claim] = []
    for line_number, raw_line in enumerate(lines[1:], start=2):
        cells = raw_line.split("\t")
        if len(cells) != len(headers):
            continue
        context = {context_key: _plain_cell(cells[0])}
        for column, metric in enumerate(metrics[1:], start=1):
            if metric is None:
                continue
            match = _NUMBER_RE.fullmatch(_plain_cell(cells[column]))
            if match is None:
                continue
            claims.append(
                Claim(
                    metric=metric,
                    value=_normalize_value(
                        metric,
                        _parse_number(match.group("value")),
                        percent=bool(match.group("percent")),
                    ),
                    raw_text=raw_line.strip(),
                    line=line_number,
                    context=context,
                )
            )
    return claims


def _duration_seconds(value: str, unit: str) -> float:
    number = _parse_number(value)
    normalized = unit.casefold()
    if normalized in {"nanosecond", "nanoseconds", "ns"}:
        return number / 1_000_000_000
    if normalized in {"microsecond", "microseconds", "µs", "μs", "us"}:
        return number / 1_000_000
    if normalized in {"millisecond", "milliseconds", "ms"}:
        return number / 1_000
    if normalized in {"minute", "minutes", "min", "mins", "m"}:
        return number * 60
    return number


def _duration_cell_seconds(cell: str) -> float | None:
    readable = _plain_cell(cell).casefold().lstrip("~≈ ")
    unit_match = _UNIT_DURATION_RE.fullmatch(readable)
    if unit_match is not None:
        return _duration_seconds(unit_match.group("value"), unit_match.group("unit"))
    plain = readable.replace(" ", "")
    match = re.fullmatch(
        rf"(?:(?P<minutes>{_NUMBER})(?:m|min|mins|minute|minutes))?"
        rf"(?:(?P<seconds>{_NUMBER})(?:s|sec|secs|second|seconds)?)?",
        plain,
    )
    if match is None or not (match.group("minutes") or match.group("seconds")):
        return None
    minutes = _parse_number(match.group("minutes") or "0")
    seconds = _parse_number(match.group("seconds") or "0")
    return minutes * 60 + seconds


def _table_context(
    headers: list[str], metrics: list[str | None], cells: list[str]
) -> dict[str, str]:
    context: dict[str, str] = {}
    for index, header in enumerate(headers):
        if index >= len(cells):
            continue
        normalized_header = re.sub(
            r"[^\w]+", " ", _plain_cell(header).casefold(), flags=re.UNICODE
        ).strip()
        key = _CONTEXT_HEADERS.get(normalized_header)
        value = _context_label(cells[index])
        if key and value and len(value) <= 200:
            context[key] = value
            continue
        if metrics[index] is not None:
            continue
    return context


def _context_label(value: str) -> str:
    return re.sub(r"^[^\w]+", "", _plain_cell(value), flags=re.UNICODE).strip()


def _normalize_value(metric: str, value: float, *, percent: bool) -> float:
    if percent or (is_unit_interval_metric(metric) and 1 < abs(value) <= 100):
        return value / 100.0
    return value


def _parse_number(raw: str) -> float:
    raw = raw.replace("−", "-")
    if re.fullmatch(r"[+-]?(?:[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d+)?", raw):
        return float(raw.replace(",", ""))
    return float(raw.replace(",", "."))


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
