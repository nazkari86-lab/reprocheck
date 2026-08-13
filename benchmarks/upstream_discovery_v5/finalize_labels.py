from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVALUATOR_COMMIT = "96e0a4688ef74e6ddc41ec78471276954c5cda66"


def source_name(case_id: str, path: str, phase: str) -> str:
    suffix = Path(path).suffix or ".txt"
    return f"{case_id}--{path.replace('/', '__')}.{phase}{suffix}"


def claim(
    case_id: str,
    file: str,
    before_snippet: str,
    after_snippet: str,
    metric: str,
    before_value: float,
    after_value: float,
    context: dict[str, str] | None = None,
) -> dict[str, Any]:
    before = (ROOT / "sources" / source_name(case_id, file, "before")).read_text(encoding="utf-8")
    after = (ROOT / "sources" / source_name(case_id, file, "after")).read_text(encoding="utf-8")
    assert before.count(before_snippet) == 1, (case_id, file, before_snippet)
    assert after.count(after_snippet) == 1, (case_id, file, after_snippet)
    result: dict[str, Any] = {
        "file": file,
        "before_snippet": before_snippet,
        "after_snippet": after_snippet,
        "metric": metric,
        "before_value": before_value,
        "after_value": after_value,
    }
    if context:
        result["context"] = context
    return result


def _web_frontier_claims() -> list[dict[str, Any]]:
    case_id = "web-frontier-failure-aware-latency"
    file = "README.md"
    providers = [
        ("string", 9.70, 11.07),
        ("scrapfly", 12.01, 14.28),
        ("bright", 24.23, 24.33),
        ("context_dev", 11.86, 13.62),
        ("firecrawl", 8.38, 14.70),
        ("scraperapi", 13.71, 13.31),
        ("oxylabs", 20.73, 20.85),
        ("zyte", 15.15, 17.50),
        ("decodo", 31.54, 29.74),
        ("nimble", 27.21, 21.43),
        ("browserbase", 2.43, 15.25),
        ("zenrows", 14.97, 21.35),
        ("scrapingant", 5.09, 15.46),
        ("scrapingdog", 4.61, 15.01),
        ("scrapingbee", 7.20, 18.15),
    ]
    claims = []
    for rank, (provider, old, new) in enumerate(providers, start=1):
        old_line = f"| {rank:>4} | {provider:<16} | " + next(
            line.split(f"| {rank:>4} | {provider:<16} | ", 1)[1]
            for line in (ROOT / "sources" / source_name(case_id, file, "before"))
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith(f"| {rank:>4} | {provider:<16} | ")
        )
        new_line = f"| {rank:>4} | {provider:<16} | " + next(
            line.split(f"| {rank:>4} | {provider:<16} | ", 1)[1]
            for line in (ROOT / "sources" / source_name(case_id, file, "after"))
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith(f"| {rank:>4} | {provider:<16} | ")
        )
        claims.append(
            claim(
                case_id,
                file,
                old_line,
                new_line,
                "latency_score_seconds",
                old,
                new,
                {"system": provider},
            )
        )
    return claims


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(case_id: str, rank: int, file: str, claims: list[dict[str, Any]]) -> None:
        cases.append({"id": case_id, "rank": rank, "files": [file], "claims": claims})

    case_id, file = "openadapt-saved-row-success-correction", "benchmark/openemr/BENCHMARK.md"
    add(
        case_id,
        28,
        file,
        [
            claim(
                case_id,
                file,
                "| success rate | 100% (20/20) | 100% (10/10) |",
                "| success rate | 95% (19/20) | 100% (10/10) |",
                "success_rate",
                1.0,
                0.95,
                {"system": "compiled replay"},
            )
        ],
    )

    case_id, file = (
        "comet-speedup-formula-correction",
        "docs/source/contributor-guide/benchmarking.md",
    )
    add(
        case_id,
        35,
        file,
        [
            claim(
                case_id,
                file,
                "Comet currently provides a 35% speedup for TPC-H @ SF=100GB.",
                "Comet currently provides a 54% speedup for TPC-H @ SF=100GB.",
                "speedup",
                0.35,
                0.54,
                {"dataset": "TPC-H SF=100GB"},
            ),
            claim(
                case_id,
                file,
                "Comet currently provides an 18% speedup for TPC-DS @ SF=100GB.",
                "Comet currently provides an 23% speedup for TPC-DS @ SF=100GB.",
                "speedup",
                0.18,
                0.23,
                {"dataset": "TPC-DS SF=100GB"},
            ),
        ],
    )

    case_id, file = "turbovec-drifted-arm-speed-range", "README.md"
    old = "On ARM, TurboQuant beats FAISS FastScan by 16–24% across every config."
    new = "On ARM, TurboQuant beats FAISS FastScan by 19–31% across every config."
    add(
        case_id,
        71,
        file,
        [
            claim(
                case_id,
                file,
                old,
                new,
                "speedup_range_low",
                0.16,
                0.19,
                {"system": "TurboQuant", "baseline": "FAISS FastScan", "platform": "ARM"},
            ),
            claim(
                case_id,
                file,
                old,
                new,
                "speedup_range_high",
                0.24,
                0.31,
                {"system": "TurboQuant", "baseline": "FAISS FastScan", "platform": "ARM"},
            ),
        ],
    )

    add("web-frontier-failure-aware-latency", 79, "README.md", _web_frontier_claims())

    case_id, file = "kalpa-private-working-set-correction", "README.md"
    old = "- **Native performance UI (beta, Windows)** — an opt-in mode that relaunches Kalpa as one native process instead of a webview and its six helpers. With the window open that cuts resident memory to about 130 MB from about 440 MB on the same 119-addon profile. It covers addon management, the uploader, and Pack Hub. Switch back from Settings at any time; if it fails to start, Kalpa reverts to the standard UI on its own."
    new = "- **Native performance UI (beta, Windows)** — an opt-in mode that relaunches Kalpa as one native process instead of a webview and its six helpers, which cuts memory with the window open to about 85 MB from around 135 MB. The standard UI still wins once minimized, since the sidecar has no equivalent suspend. It covers addon management, the uploader, and Pack Hub. Switch back from Settings at any time; if it fails to start, Kalpa reverts to the standard UI on its own."
    add(
        case_id,
        105,
        file,
        [
            claim(case_id, file, old, new, "memory_mb", 130.0, 85.0, {"system": "native UI"}),
            claim(case_id, file, old, new, "memory_mb", 440.0, 135.0, {"system": "webview UI"}),
        ],
    )

    case_id, file = "markforge-dedup-recall-correction", "docs/AGENTIFY.md"
    add(
        case_id,
        247,
        file,
        [
            claim(
                case_id,
                file,
                "| authored pairs merged | **1 of 2** |",
                "| **recall** — authored near-duplicate pairs merged | **0 of 2** |",
                "recall",
                0.5,
                0.0,
                {"task": "authored near-duplicate pairs"},
            )
        ],
    )

    case_id, file = (
        "sage-specificity-precision-correction",
        "docs/arabic-poc-study-readiness-2026-06-05.md",
    )
    old = "- Crisis path for English: S1 lexicon + S3 semantic OR-fusion. Measured recall: **37.1%** (86/232 CRADLE cases). Precision: **95.7%**. KPI is ≥95% recall — gap is **57.9 points**."
    new = '- Crisis path for English: S1 lexicon + S3 semantic OR-fusion. Measured recall: **37.1%** (86/232 CRADLE cases). Specificity: **95.7%** (178/186). Precision: **91.5%** (86/94). KPI is ≥95% recall — gap is **57.9 points**. (Corrected 2026-06-15: the 95.7% figure was previously mislabeled "precision"; it is specificity. True precision is 91.5%, given the frozen 2026-06-05 numerators — see tests/test_cradle_bench.py header.)'
    add(
        case_id,
        263,
        file,
        [
            claim(
                case_id,
                file,
                old,
                new,
                "precision",
                0.957,
                0.915,
                {"system": "S1 lexicon + S3 semantic OR-fusion", "dataset": "CRADLE"},
            )
        ],
    )

    case_id, file = "container-system-baseline-sync", "README.md"
    rows = [
        ("Container System Binary", "2M/s", "1.8M", 2_000_000.0, 1_800_000.0),
        ("MessagePack", "1.8M/s", "1.6M", 1_800_000.0, 1_600_000.0),
        ("JSON (nlohmann)", "400K/s", "950K", 400_000.0, 950_000.0),
        ("XML (pugixml)", "200K/s", "720K", 200_000.0, 720_000.0),
    ]
    container_claims = []
    before_text = (ROOT / "sources" / source_name(case_id, file, "before")).read_text(
        encoding="utf-8"
    )
    after_text = (ROOT / "sources" / source_name(case_id, file, "after")).read_text(
        encoding="utf-8"
    )
    for system, old_token, new_token, old_value, new_value in rows:
        before_line = next(
            line for line in before_text.splitlines() if system in line and old_token in line
        )
        after_line = next(
            line for line in after_text.splitlines() if system in line and new_token in line
        )
        container_claims.append(
            claim(
                case_id,
                file,
                before_line,
                after_line,
                "throughput_ops_per_second",
                old_value,
                new_value,
                {"system": system},
            )
        )
    add(case_id, 350, file, container_claims)

    case_id, file = "graph-invariant-paper-number-audit", "paper/sections/results.tex"
    add(
        case_id,
        363,
        file,
        [
            claim(
                case_id,
                file,
                "ASPL experiment converges from a composite fitness score of 0.426 to 0.553",
                "ASPL experiment converges from a composite fitness score of 0.426 to 0.552",
                "score",
                0.553,
                0.552,
                {"experiment": "ASPL MAP-Elites final composite fitness"},
            )
        ],
    )

    case_id, file = "ssik-uncompiled-latency-correction", "README.md"
    ssik_rows = [
        ("Gen3", "51.25", "40.75", 0.05125, 0.04075),
        ("xArm7", "8.87", "6.87", 0.00887, 0.00687),
        ("PiPER", "2.50", "2.01", 0.00250, 0.00201),
    ]
    before_text = (ROOT / "sources" / source_name(case_id, file, "before")).read_text(
        encoding="utf-8"
    )
    after_text = (ROOT / "sources" / source_name(case_id, file, "after")).read_text(
        encoding="utf-8"
    )
    ssik_claims = []
    for system, old_token, new_token, old_value, new_value in ssik_rows:
        before_line = next(
            line
            for line in before_text.splitlines()
            if line.startswith(f"| {system} ") and f"| {old_token} " in line
        )
        after_line = next(
            line
            for line in after_text.splitlines()
            if line.startswith(f"| {system} ") and f"| {new_token} " in line
        )
        ssik_claims.append(
            claim(
                case_id,
                file,
                before_line,
                after_line,
                "runtime_seconds",
                old_value,
                new_value,
                {"system": system, "implementation": "ssik"},
            )
        )
    add(case_id, 393, file, ssik_claims)

    case_id, file = "hangman-dictionary-metric-correction", "analysis/difficulty_report.tsv"
    before_text = (ROOT / "sources" / source_name(case_id, file, "before")).read_text(
        encoding="utf-8"
    )
    after_text = (ROOT / "sources" / source_name(case_id, file, "after")).read_text(
        encoding="utf-8"
    )
    hangman_claims = []
    for word, old_value, new_value in (("dwarves", 16.0, 1.0), ("pyjamas", 19.0, 2.0)):
        before_line = next(
            line for line in before_text.splitlines() if line.startswith(f"{word}\t")
        )
        after_line = next(line for line in after_text.splitlines() if line.startswith(f"{word}\t"))
        hangman_claims.append(
            claim(
                case_id,
                file,
                before_line,
                after_line,
                "wrong_coverage",
                old_value,
                new_value,
                {"word": word},
            )
        )
    add(case_id, 395, file, hangman_claims)
    return cases


def main() -> int:
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    cases = build_cases()
    by_rank = {item["sample_rank"]: item for item in details}
    eligible = {case["rank"]: case for case in cases}
    labels = []
    review = json.loads((ROOT / "review_packet.json").read_text(encoding="utf-8"))["reviews"]
    reviews_by_rank = {item["rank"]: item for item in review}
    for item in sorted(details, key=lambda value: value["sample_rank"]):
        rank = item["sample_rank"]
        if rank in eligible:
            label = {
                "rank": rank,
                "repository": item["repository"],
                "pull_request": item["pull_request"],
                "eligible": True,
                "case_id": eligible[rank]["id"],
                "reason": "same-scope numeric report correction with unique immutable snippets",
            }
        else:
            review_item = reviews_by_rank[rank]
            structural = not review_item["paired_numeric_report_files"]
            reason = (
                "no paired removed-and-added numeric lines in an available human-readable report patch"
                if structural
                else "manual semantic review: new experiment/config/version/dataset, non-empirical number, or no uniquely groundable same-scope correction"
            )
            label = {
                "rank": rank,
                "repository": item["repository"],
                "pull_request": item["pull_request"],
                "eligible": False,
                "reason": reason,
            }
        labels.append(label)
    for case in cases:
        item = by_rank[case["rank"]]
        case["repository"] = item["repository"]
        case["pull_request"] = item["pull_request"]
        case["url"] = item["url"]
        del case["rank"]
    labels_payload = {
        "schema_version": "reprocheck.upstream-discovery-labels.v5",
        "parser_output_used": False,
        "sample_size": len(labels),
        "eligible_cases": len(cases),
        "labels": labels,
    }
    cases_payload = {
        "schema_version": "reprocheck.upstream-discovery-cases.v5",
        "evaluator_commit": EVALUATOR_COMMIT,
        "parser_output_used": False,
        "cases": cases,
    }
    (ROOT / "labels.json").write_text(
        json.dumps(labels_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "cases.json").write_text(
        json.dumps(cases_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "sample_size": len(labels),
                "eligible_cases": len(cases),
                "selected_claims": sum(len(case["claims"]) for case in cases),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
