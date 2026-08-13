from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVALUATOR_COMMIT = "901352b"


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
    context: dict[str, str],
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
        "context": context,
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(case_id: str, rank: int, file: str, claims: list[dict[str, Any]]) -> None:
        cases.append({"id": case_id, "rank": rank, "files": [file], "claims": claims})

    case_id, file = "oans-stale-hashfile-sizes", "README.md"
    old = "| Compact 64-bit path-hash index | Smaller hashfile (**41 vs 73 MiB** on the benchmark tree), faster path lookups |"
    new = "| Compact 64-bit path-hash index | Smaller hashfile (**39.7 vs 70.9 MiB** on the larger-than-RAM tree), faster path lookups |"
    add(
        case_id,
        38,
        file,
        [
            selected_claim(
                case_id, file, old, new, "memory_mb", 41.0, 39.7, {"system": "path-hash index"}
            ),
            selected_claim(
                case_id, file, old, new, "memory_mb", 73.0, 70.9, {"system": "full-path index"}
            ),
        ],
    )

    case_id, file = "inferedge-rknn-document-sync", "README.md"
    old_fp16 = "| FP16 | 22.764 ms | 0.621 | 기준 결과 |"
    new_fp16 = "| FP16 | 51.82 ms | 0.7791 | 기준 결과 |"
    old_int8 = "| INT8 | 15.403 ms | 0.612 | 더 빠르지만 accuracy trade-off 존재 |"
    new_int8 = "| Hybrid INT8 | 16.29 ms | 0.7977 | 더 빠르면서 accuracy도 유지/개선 |"
    add(
        case_id,
        70,
        file,
        [
            selected_claim(
                case_id,
                file,
                old_fp16,
                new_fp16,
                "avg_latency_seconds",
                0.022764,
                0.05182,
                {"system": "FP16"},
            ),
            selected_claim(
                case_id, file, old_fp16, new_fp16, "map50", 0.621, 0.7791, {"system": "FP16"}
            ),
            selected_claim(
                case_id,
                file,
                old_int8,
                new_int8,
                "avg_latency_seconds",
                0.015403,
                0.01629,
                {"system": "INT8"},
            ),
            selected_claim(
                case_id, file, old_int8, new_int8, "map50", 0.612, 0.7977, {"system": "INT8"}
            ),
        ],
    )

    case_id, file = "scbe-stale-test-count", "README.md"
    old = "| 6,066 tests | Verification | 5,954 TypeScript + 112 Python; property-based with fast-check/Hypothesis |"
    new = "| ~19,170 tests | Verification | 5,954 TypeScript + **13,216 Python** (`pytest --collect-only`, 2026-07-25, all under `tests/`); property-based with fast-check/Hypothesis |"
    add(
        case_id,
        151,
        file,
        [
            selected_claim(
                case_id, file, old, new, "test_count", 6066.0, 19170.0, {"scope": "total"}
            ),
            selected_claim(
                case_id, file, old, new, "test_count", 112.0, 13216.0, {"scope": "Python"}
            ),
        ],
    )

    case_id = "hood-river-vad-config-correction"
    file = "backend/pipeline/segmentation/tests/VAD_BENCHMARKS.md"
    old = "| **`test_vad_inter_transmission_gap_speech.flac`** | **0.794** | `0.658` | `1.000` | Watch Duty live feed inter-transmission gap with short speech bursts (`c1416cf1`). |"
    new = "| **`test_vad_inter_transmission_gap_speech.flac`** | **0.791** | `0.687` | `0.932` | Oregon Hood River (`bcfy_feeds`) 15s stream chunk (`c1416cf1`): inter-transmission gap with short quiet bursts. Production-shaped VAD input. The 0.068 recall gap is edge clipping, not a dropped burst: `0.532-0.832`, `5.696-5.872`, `6.672-6.848`. At production `pad_sec = 0.3` this file scores `0.794` / `0.659` / `1.000`. |"
    context = {"system": "test_vad_inter_transmission_gap_speech.flac"}
    add(
        case_id,
        153,
        file,
        [
            selected_claim(case_id, file, old, new, "f1", 0.794, 0.791, context),
            selected_claim(case_id, file, old, new, "precision", 0.658, 0.687, context),
            selected_claim(case_id, file, old, new, "recall", 1.0, 0.932, context),
        ],
    )
    return cases


def main() -> int:
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    review = json.loads((ROOT / "review_packet.json").read_text(encoding="utf-8"))["reviews"]
    assert len(sample["samples"]) == len(details) == len(review) == 160
    cases = build_cases()
    by_rank = {item["sample_rank"]: item for item in details}
    eligible = {case["rank"]: case for case in cases}
    labels = []
    for item in sorted(details, key=lambda value: value["sample_rank"]):
        rank = item["sample_rank"]
        if rank in eligible:
            reason = "same-scope stale or misconfigured numeric report correction"
            case_id = eligible[rank]["id"]
        else:
            reason = "no eligible same-scope empirical correction after manual semantic review"
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
        case.update(
            repository=item["repository"],
            pull_request=item["pull_request"],
            url=item["url"],
        )
    (ROOT / "labels.json").write_text(
        json.dumps(
            {
                "schema_version": "reprocheck.upstream-discovery-labels.v7",
                "parser_output_used": False,
                "sample_size": 160,
                "eligible_cases": len(cases),
                "labels": labels,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (ROOT / "cases.json").write_text(
        json.dumps(
            {
                "schema_version": "reprocheck.upstream-discovery-cases.v7",
                "evaluator_commit": EVALUATOR_COMMIT,
                "parser_output_used": False,
                "cases": cases,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print({"sample": 160, "eligible": len(cases), "claims": sum(len(c["claims"]) for c in cases)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
