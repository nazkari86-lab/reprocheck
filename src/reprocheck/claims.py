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

_ALIASES = "|".join(
    sorted((re.escape(k) for k in METRIC_ALIASES if k != "score"), key=len, reverse=True)
)
_NUMBER = r"[+\-−]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+\-−]?\d+)?"
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
    rf"(?P<unit>microseconds?|µs|us|milliseconds?|ms|seconds?|secs?|s)\b",
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
                    float(coco_match.group("value").replace(",", ".")),
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
            value = float(match.group("value").replace(",", "."))
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
                float(match.group("value").replace(",", ".")),
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
            value = float(match.group("value").replace(",", "."))
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
                float(match.group("value").replace(",", ".")),
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
                float(match.group("value").replace(",", ".")),
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
                value = float(match.group("value").replace(",", "."))
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
    claims.sort(key=lambda claim: claim.line)
    return claims


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
            value = float(jmh.group("value").replace(",", "."))
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
    return float(raw.replace(",", "."))


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
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
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
    minutes = float((match.group("minutes") or "0").replace(",", "."))
    seconds = float((match.group("seconds") or "0").replace(",", "."))
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
    if re.fullmatch(r"[+-]?[1-9]\d{0,2},\d{3}", raw):
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
