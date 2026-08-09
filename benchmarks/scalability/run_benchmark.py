from __future__ import annotations

import json
import platform
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from reprocheck.audit import run_audit
from reprocheck.certificate import verify_certificate_file
from reprocheck.version import __version__


SIZES = (10, 100, 1000)
REPEATS = 5


def run(output: Path | None = None) -> dict[str, Any]:
    cases = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-scalability-") as directory:
        root = Path(directory)
        for size in SIZES:
            report_path = root / f"report-{size}.md"
            report_path.write_text(_report(size), encoding="utf-8")
            durations = []
            structural = []
            for repeat in range(REPEATS):
                started = time.perf_counter_ns()
                audit = run_audit(report_path=report_path)
                certificate_path = root / f"certificate-{size}-{repeat}.json"
                certificate_path.write_text(
                    json.dumps(audit.to_dict(), ensure_ascii=False, sort_keys=True),
                    encoding="utf-8",
                )
                errors = verify_certificate_file(certificate_path)
                durations.append((time.perf_counter_ns() - started) / 1_000_000)
                graph = audit.evidence_graph
                structural.append(
                    {
                        "claims": len(audit.claims),
                        "nodes": len(graph.nodes) if graph else 0,
                        "edges": len(graph.edges) if graph else 0,
                        "certificate_bytes": certificate_path.stat().st_size,
                        "verification_errors": errors,
                    }
                )
            deterministic = structural[0]
            cases.append(
                {
                    "declared_claims": size,
                    "repeats": REPEATS,
                    "exact_claim_count_all_repeats": all(
                        item["claims"] == size for item in structural
                    ),
                    "valid_certificate_all_repeats": all(
                        not item["verification_errors"] for item in structural
                    ),
                    "structural_result_stable": all(item == deterministic for item in structural),
                    "graph_nodes": deterministic["nodes"],
                    "graph_edges": deterministic["edges"],
                    "certificate_bytes": deterministic["certificate_bytes"],
                    "median_wall_ms": statistics.median(durations),
                    "min_wall_ms": min(durations),
                    "max_wall_ms": max(durations),
                }
            )
    result = {
        "schema": "reprocheck.scalability-result.v1",
        "tool_version": __version__,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "cases": cases,
        "summary": {
            "sizes": list(SIZES),
            "repeats_per_size": REPEATS,
            "all_claim_counts_exact": all(case["exact_claim_count_all_repeats"] for case in cases),
            "all_certificates_valid": all(case["valid_certificate_all_repeats"] for case in cases),
            "all_structural_results_stable": all(
                case["structural_result_stable"] for case in cases
            ),
        },
        "scientific_boundary": (
            "Synthetic scaling curve; deterministic structural outcomes are gated, while wall "
            "times are descriptive and environment-dependent."
        ),
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def _report(size: int) -> str:
    rows = ["| Model | Accuracy |", "| --- | ---: |"]
    rows.extend(f"| model-{index:04d} | {(50 + index % 50):.1f}% |" for index in range(size))
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/scalability.json"))
    args = parser.parse_args()
    benchmark = run(args.output)
    print(json.dumps(benchmark["summary"], sort_keys=True))
