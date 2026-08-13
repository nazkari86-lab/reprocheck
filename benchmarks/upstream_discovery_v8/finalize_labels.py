from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FROZEN_PARSER_COMMIT = "6238f2c"


def source_name(case_id: str, path: str, phase: str) -> str:
    suffix = Path(path).suffix or ".txt"
    return f"{case_id}--{path.replace('/', '__')}.{phase}{suffix}"


def selected_claim(
    case_id: str,
    file: str,
    before_snippet: str,
    after_snippet: str,
    metric: str,
    before_value: float,
    after_value: float,
    context: dict[str, str] | None = None,
) -> dict[str, Any]:
    before = (ROOT / "sources" / source_name(case_id, file, "before")).read_text()
    after = (ROOT / "sources" / source_name(case_id, file, "after")).read_text()
    assert before.count(before_snippet) == after.count(after_snippet) == 1
    return {
        "file": file,
        "before_snippet": before_snippet,
        "after_snippet": after_snippet,
        "metric": metric,
        "before_value": before_value,
        "after_value": after_value,
        "context": context or {},
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(case_id: str, rank: int, file: str, claims: list[dict[str, Any]]) -> None:
        cases.append({"id": case_id, "rank": rank, "files": [file], "claims": claims})

    case_id, file = "vize-benchmark-snapshot-reconciliation", "README.md"
    old_vite = "| Vite build  | @vitejs/plugin-vue |    1.70s |   1.52s |   **1.1×** |"
    new_vite = "| Vite build  |  1,000 | @vitejs/plugin-vue |    1.66s | 732.5ms |   **2.3×** |"
    old_nuxt = "| Nuxt build  | Nuxt compiler      |    6.68s |   7.35s |   **0.9×** |"
    new_nuxt = "| Nuxt build  |    500 | Nuxt compiler      |    6.79s |   6.42s |  **1.1×**† |"
    add(
        case_id,
        153,
        file,
        [
            selected_claim(case_id, file, old_vite, new_vite, "speedup", 1.1, 2.3, {"system": "Vite build"}),
            selected_claim(case_id, file, old_nuxt, new_nuxt, "speedup", 0.9, 1.1, {"system": "Nuxt build"}),
        ],
    )

    case_id, file = "navsentinel-stale-test-count", "docs/Testing_and_Gym.md"
    add(
        case_id,
        169,
        file,
        [selected_claim(case_id, file, "2,874 passing unit", "3,010 passing", "test_count", 2874, 3010, {"scope": "total"})],
    )

    case_id, file = "trusta-offload-attribution", "wiki/en/concepts/offload-mechanism.md"
    add(
        case_id,
        170,
        file,
        [selected_claim(case_id, file, "peak of **~13.4 GB GPU VRAM**", "peak of **~11.7 GB GPU VRAM**", "memory_mb", 13721.6, 11980.8, {"system": "Qwen3-14B bf16"})],
    )

    case_id, file = "agentmemory-p-at-five-correction", "README.md"
    old_hybrid = "| **agentmemory hybrid** | **0.578** | **0.967** | **15 / 15** | 14 ms |"
    new_hybrid = "| **agentmemory hybrid** | **0.240** | **1.000** | **15 / 15** | 14 ms |"
    old_grep = "| grep baseline | 0.267 | 0.967 | 15 / 15 | 0 ms |"
    new_grep = "| grep baseline | 0.227 | 0.967 | 15 / 15 | 0 ms |"
    add(
        case_id,
        303,
        file,
        [
            selected_claim(case_id, file, old_hybrid, new_hybrid, "precision_5", 0.578, 0.240, {"model": "agentmemory hybrid"}),
            selected_claim(case_id, file, old_hybrid, new_hybrid, "recall_5", 0.967, 1.000, {"model": "agentmemory hybrid"}),
            selected_claim(case_id, file, old_grep, new_grep, "precision_5", 0.267, 0.227, {"model": "grep baseline"}),
        ],
    )

    simple_counts = [
        ("ace-tracker-stale-test-count", 456, "All 34 tests must pass", "All 48 tests must pass", 34, 48),
        ("coursework-wrapper-test-count", 458, "There are 29 in total", "There are 39 in total", 29, 39),
        ("trading-agent-stale-test-count", 460, "**1,729 tests as of", "**1,864 tests as of", 1729, 1864),
        ("chatapp-test-coverage-count", 462, "**370 tests** repartidos", "**475 tests** repartidos", 370, 475),
        ("edith-stale-test-count", 464, "**410 passed, 2 skipped**", "**416 passed, 2 skipped**", 410, 416),
        ("coffergate-test-count", 472, "121개 자동 테스트", "124개 자동 테스트", 121, 124),
        ("sealrail-test-count", 474, "769 tests across 17 files", "770 tests across 17 files", 769, 770),
    ]
    for case_id, rank, old, new, before_value, after_value in simple_counts:
        add(
            case_id,
            rank,
            "README.md",
            [selected_claim(case_id, "README.md", old, new, "test_count", before_value, after_value, {"scope": "total"})],
        )

    case_id, file = "calm-measured-summary-refresh", "README.md"
    calm_rows = [
        ("Hub concentration (`hub_pct`)", "7.5%", "7.6%", "hub_pct", 0.075, 0.076),
        ("Dead-code rate (`dead_code_pct`, coverage-aware)", "5.0%", "5.6%", "dead_code_pct", 0.050, 0.056),
        ("Edge coverage (`edge_coverage_pct`)", "74.9%", "70.1%", "edge_coverage_pct", 0.749, 0.701),
        ("High-complexity functions (`high_complexity_pct`)", "2.9%", "2.8%", "high_complexity_pct", 0.029, 0.028),
    ]
    calm_claims = []
    for label, old, new, metric, before_value, after_value in calm_rows:
        calm_claims.append(
            selected_claim(case_id, file, f"| {label} | {old}", f"| {label} | {new}", metric, before_value, after_value)
        )
    add(case_id, 528, file, calm_claims)

    case_id, file = "ai-architect-test-count", "README.md"
    add(case_id, 532, file, [selected_claim(case_id, file, "629 tests. Every numeric", "877 tests. Every numeric", "test_count", 629, 877, {"scope": "total"})])

    case_id, file = "clickllm-published-counts", "README.md"
    old = "**983 tests.** 756 Python, 227 Rust."
    new = "**992 tests.** 765 Python, 227 Rust."
    add(
        case_id,
        548,
        file,
        [
            selected_claim(case_id, file, old, new, "test_count", 983, 992, {"scope": "total"}),
            selected_claim(case_id, file, old, new, "test_count", 756, 765, {"scope": "Python"}),
        ],
    )

    case_id, file = "uteke-readme-fact-check", "README.md"
    add(
        case_id,
        752,
        file,
        [
            selected_claim(case_id, file, "| **Recall speed** | ~30ms", "| **Recall speed** | ~45ms", "runtime_seconds", 0.030, 0.045, {"system": "recall"}),
            selected_claim(case_id, file, "with 327 unit tests", "with 206 tests", "test_count", 327, 206, {"scope": "total"}),
        ],
    )

    case_id, file = "topogeoml-test-count", "STATUS.md"
    add(case_id, 772, file, [selected_claim(case_id, file, "| Tests | 500 |", "| Tests | 504 |", "test_count", 500, 504, {"scope": "total"})])
    return cases


def main() -> int:
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    review = json.loads((ROOT / "review_packet.json").read_text(encoding="utf-8"))["reviews"]
    assert len(sample["samples"]) == len(details) == len(review) == 994
    cases = build_cases()
    by_rank = {item["sample_rank"]: item for item in details}
    eligible = {case["rank"]: case for case in cases}
    special_reasons = {
        181: "selected immutable source is identical before and after merge; no auditable correction pair",
        545: "corrected result is introduced only in the after artifact; selected before artifact has no prior numeric result",
    }
    labels = []
    for item in sorted(details, key=lambda value: value["sample_rank"]):
        rank = item["sample_rank"]
        if rank in eligible:
            reason = "same-scope empirical report correction with immutable before and after evidence"
            case_id = eligible[rank]["id"]
        else:
            reason = special_reasons.get(
                rank, "no eligible same-scope empirical correction after source-diff semantic review"
            )
            case_id = None
        label = {
            "rank": rank,
            "repository": item["repository"],
            "pull_request": item["pull_request"],
            "eligible": rank in eligible,
            "reason": reason,
        }
        if case_id:
            label["case_id"] = case_id
        labels.append(label)
    for case in cases:
        item = by_rank[case.pop("rank")]
        case.update(repository=item["repository"], pull_request=item["pull_request"], url=item["url"])
    (ROOT / "labels.json").write_text(
        json.dumps(
            {
                "schema_version": "reprocheck.upstream-discovery-labels.v8",
                "parser_output_used": False,
                "sample_size": 994,
                "eligible_cases": len(cases),
                "labels": labels,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (ROOT / "cases.json").write_text(
        json.dumps(
            {
                "schema_version": "reprocheck.upstream-discovery-cases.v8",
                "evaluator_commit": FROZEN_PARSER_COMMIT,
                "parser_output_used": False,
                "cases": cases,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print({"sample": 994, "eligible": len(cases), "claims": sum(len(case["claims"]) for case in cases)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
