from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def c(line: int, metric: str, value: float) -> dict[str, Any]:
    return {"line": line, "metric": metric, "value": value}


def e(
    rank: int, reason: str, block: tuple[int, int], claims: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "rank": rank,
        "eligible": True,
        "reason": reason,
        "block_lines": list(block),
        "claims": claims,
    }


def x(rank: int, reason: str) -> dict[str, Any]:
    return {"rank": rank, "eligible": False, "reason": reason, "claims": []}


CASES = [
    e(
        1,
        "first summary block has eight supported retrieval, reliability, latency, and classification outcomes",
        (14, 23),
        [
            c(16, "hit_rate", 0.978),
            c(17, "mrr", 0.9725),
            c(18, "fail_rate", 0),
            c(19, "p95_latency_seconds", 0.52655),
            c(20, "accuracy", 1),
            c(21, "accuracy", 1),
            c(22, "accuracy", 0.9),
            c(23, "recall", 0.8),
        ],
    ),
    e(
        2,
        "first size-conforming result table has ten supported classification outcomes",
        (127, 130),
        [
            c(129, "accuracy", 0.714),
            c(129, "recall", 0.648),
            c(129, "precision", 0.734),
            c(129, "recall", 0.777),
            c(129, "macro_f1", 0.712),
            c(130, "accuracy", 0.678),
            c(130, "recall", 0.854),
            c(130, "precision", 0.578),
            c(130, "recall", 0.552),
            c(130, "macro_f1", 0.678),
        ],
    ),
    e(
        3,
        "first detection table has three supported outcomes",
        (29, 34),
        [c(31, "recall", 0.995), c(33, "precision", 1), c(34, "f1", 0.997)],
    ),
    e(
        4,
        "executive summary has four supported classification outcomes",
        (11, 17),
        [
            c(11, "accuracy", 0.764),
            c(11, "accuracy", 0.888),
            c(16, "precision", 0.88),
            c(17, "accuracy", 0.98),
        ],
    ),
    x(5, "first principal result table exceeds twenty supported outcomes"),
    e(
        6,
        "first size-conforming supported table has precision, recall, and F1",
        (51, 53),
        [c(53, "precision", 1), c(53, "recall", 1), c(53, "f1", 1)],
    ),
    x(7, "no contiguous block contains three supported public-ontology outcomes"),
    e(
        8,
        "first retrieval-quality table has ten supported Hit-rate and MRR outcomes",
        (33, 43),
        [
            c(38, "hit_rate", 0.7333),
            c(38, "hit_rate", 0.6154),
            c(39, "hit_rate", 0.9),
            c(39, "hit_rate", 0.7692),
            c(40, "hit_rate", 0.9),
            c(40, "hit_rate", 0.9231),
            c(41, "mrr", 0.8),
            c(41, "mrr", 0.7179),
            c(42, "hit_rate", 0.9),
            c(42, "hit_rate", 0.9231),
        ],
    ),
    e(
        9,
        "first size-conforming latency distribution has p95, standard deviation, and mean",
        (199, 210),
        [
            c(205, "p95_latency_seconds", 0.0321),
            c(209, "latency_stdev_seconds", 0.0042),
            c(210, "avg_latency_seconds", 0.0198),
        ],
    ),
    e(
        10,
        "first size-conforming score table has six mean scores",
        (28, 35),
        [
            c(30, "score", 0.457),
            c(31, "score", 0.732),
            c(32, "score", 0.434),
            c(33, "score", 0.699),
            c(34, "score", 0.433),
            c(35, "score", 0.409),
        ],
    ),
    e(
        11,
        "training-results table has eight supported perplexity, accuracy, and duration outcomes",
        (29, 38),
        [
            c(32, "perplexity", 28.7),
            c(32, "perplexity", 20.1),
            c(33, "accuracy", 0.22),
            c(33, "accuracy", 0.324),
            c(35, "runtime_seconds", 33),
            c(35, "runtime_seconds", 16),
            c(36, "runtime_seconds", 1680),
            c(36, "runtime_seconds", 780),
        ],
    ),
    e(
        12,
        "key-metrics table has one accuracy and two average-latency outcomes",
        (12, 17),
        [
            c(14, "accuracy", 0.6),
            c(17, "avg_latency_seconds", 3.796),
            c(17, "avg_latency_seconds", 0.8),
        ],
    ),
    e(
        13,
        "performance summary has five supported measured throughput, hit-rate, and memory outcomes",
        (12, 17),
        [
            c(14, "requests_per_second", 10_000_000),
            c(14, "requests_per_second", 14_000_000),
            c(16, "hit_rate", 0.99),
            c(16, "hit_rate", 0.999),
            c(17, "memory_mb", 50),
        ],
    ),
    e(
        14,
        "first console block has three supported elapsed-time outcomes",
        (14, 29),
        [
            c(17, "runtime_seconds", 0.90636),
            c(22, "runtime_seconds", 22.76476),
            c(27, "runtime_seconds", 23.67112),
        ],
    ),
    x(
        15,
        "document explicitly labels its first benchmark values as expected baselines rather than measurements",
    ),
    e(
        16,
        "summary table has five supported rates and runtime outcomes",
        (8, 14),
        [
            c(10, "success_rate", 1),
            c(11, "fail_rate", 0),
            c(12, "runtime_seconds", 230.81),
            c(13, "runtime_seconds", 214.25),
            c(14, "runtime_seconds", 376.25),
        ],
    ),
    e(
        17,
        "first size-conforming summary table has eight runtime and four speedup outcomes",
        (267, 272),
        [
            c(269, "runtime_seconds", 0.000107),
            c(269, "runtime_seconds", 0.000114),
            c(269, "speedup", 1.07),
            c(270, "runtime_seconds", 0.250),
            c(270, "runtime_seconds", 0.290),
            c(270, "speedup", 1.16),
            c(271, "runtime_seconds", 0.000368),
            c(271, "runtime_seconds", 0.000239),
            c(271, "speedup", 1.54),
            c(272, "runtime_seconds", 0.000217),
            c(272, "runtime_seconds", 0.000168),
            c(272, "speedup", 1.29),
        ],
    ),
    x(18, "measurement guidance contains no empirical result block"),
    e(
        19,
        "first individual-system block has supported runtime, throughput, memory, and wall-time outcomes",
        (21, 29),
        [
            c(23, "runtime_seconds", 0.72),
            c(24, "throughput_ops_per_second", 6_940_000),
            c(25, "memory_mb", 500),
            c(29, "runtime_seconds", 3600),
        ],
    ),
    e(
        20,
        "benchmark table has twelve supported runtime, memory, throughput, and speedup outcomes",
        (16, 20),
        [
            c(18, "runtime_seconds", 2.13),
            c(18, "peak_rss_mb", 176.6),
            c(18, "throughput_ops_per_second", 55.9),
            c(18, "speedup", 1),
            c(19, "runtime_seconds", 0.77),
            c(19, "peak_rss_mb", 289.9),
            c(19, "throughput_ops_per_second", 154.1),
            c(19, "speedup", 2.75),
            c(20, "runtime_seconds", 0.003),
            c(20, "peak_rss_mb", 323),
            c(20, "throughput_ops_per_second", 43781.9),
            c(20, "speedup", 399.4),
        ],
    ),
    e(
        21,
        "first size-conforming microbenchmark table has nine runtime outcomes",
        (35, 39),
        [
            c(37, "runtime_seconds", 0.00111),
            c(37, "runtime_seconds", 0.00124),
            c(37, "runtime_seconds", 0.00129),
            c(38, "runtime_seconds", 0.00742),
            c(38, "runtime_seconds", 0.00705),
            c(38, "runtime_seconds", 0.00682),
            c(39, "runtime_seconds", 0.0385),
            c(39, "runtime_seconds", 0.033),
            c(39, "runtime_seconds", 0.0305),
        ],
    ),
    e(
        22,
        "first comparison table has four supported runtime outcomes",
        (11, 17),
        [
            c(13, "runtime_seconds", 0.353),
            c(13, "runtime_seconds", 0.051),
            c(15, "runtime_seconds", 0.00177),
            c(15, "runtime_seconds", 0.00026),
        ],
    ),
    e(
        23,
        "first result table has five runtime and five memory outcomes",
        (12, 18),
        [
            c(14, "runtime_seconds", 0.07234),
            c(14, "memory_mb", 0.76),
            c(15, "runtime_seconds", 0.06073),
            c(15, "memory_mb", 1.29),
            c(16, "runtime_seconds", 0.00121),
            c(16, "memory_mb", 0.01),
            c(17, "runtime_seconds", 0.05246),
            c(17, "memory_mb", 0.43),
            c(18, "runtime_seconds", 0.15601),
            c(18, "memory_mb", 0.07),
        ],
    ),
    x(
        24,
        "document's first measurement blocks use unsupported P75, TTFB, LCP, bundle, and query-count identifiers",
    ),
    e(
        25,
        "first performance table has four supported request-rate and hit-rate outcomes",
        (44, 51),
        [
            c(46, "requests_per_second", 3600),
            c(46, "requests_per_second", 12091),
            c(50, "hit_rate", 0.95),
            c(50, "hit_rate", 1),
        ],
    ),
    e(
        26,
        "benchmark-results section has six supported measured runtime outcomes",
        (7, 37),
        [
            c(10, "runtime_seconds", 0.0000034787),
            c(15, "runtime_seconds", 0.00000002944),
            c(20, "runtime_seconds", 0.0000035391),
            c(25, "runtime_seconds", 0.0000010139),
            c(30, "runtime_seconds", 0.0000066308),
            c(35, "runtime_seconds", 0.0000039678),
        ],
    ),
    e(
        27,
        "first size-conforming findings section has six supported rate and latency outcomes",
        (29, 47),
        [
            c(31, "success_rate", 1),
            c(32, "avg_latency_seconds", 0.015),
            c(35, "avg_latency_seconds", 0.00028),
            c(36, "max_latency_seconds", 0.006),
            c(45, "throughput_ops_per_second", 9656),
            c(47, "throughput_ops_per_second", 2000),
        ],
    ),
    e(
        28,
        "first experiment table has exactly twenty supported runtime outcomes",
        (10, 21),
        [
            c(line, "runtime_seconds", value / 1000)
            for line, values in [
                (12, (1.08, 314.25)),
                (13, (2.06, 274.61)),
                (14, (1, 283.34)),
                (15, (0.22, 202.52)),
                (16, (3.36, 236.96)),
                (17, (3.69, 218.02)),
                (18, (0.95, 199.61)),
                (19, (1.30, 240.24)),
                (20, (0.41, 222.21)),
                (21, (1.65, 278.42)),
            ]
            for value in values
        ],
    ),
    e(
        29,
        "first results table has eight supported classification outcomes",
        (13, 20),
        [
            c(16, "accuracy", 0.777),
            c(16, "accuracy", 0.722),
            c(17, "f1", 0.662),
            c(17, "f1", 0.616),
            c(18, "precision", 0.665),
            c(18, "precision", 0.621),
            c(19, "recall", 0.777),
            c(19, "recall", 0.722),
        ],
    ),
    e(
        30,
        "first size-conforming document table has fourteen supported accuracy outcomes",
        (31, 48),
        [
            c(line, "accuracy", value)
            for line, value in [
                (33, 1),
                (34, 0.98),
                (35, 1),
                (36, 1),
                (37, 1),
                (38, 1),
                (39, 1),
                (40, 1),
                (42, 1),
                (43, 1),
                (44, 0.95),
                (46, 1),
                (47, 1),
                (48, 1),
            ]
        ],
    ),
    e(
        31,
        "first overall table has six supported MAE and RMSE outcomes",
        (48, 52),
        [
            c(50, "mae", 19.9822),
            c(50, "rmse", 31.3444),
            c(51, "mae", 21.8518),
            c(51, "rmse", 34.4946),
            c(52, "mae", 19.9459),
            c(52, "rmse", 31.2674),
        ],
    ),
    e(
        32,
        "metrics table has twelve supported R2, MAE, and RMSE outcomes",
        (14, 19),
        [
            c(16, "r2", -9.22803e-6),
            c(16, "mae", 1.05871),
            c(16, "rmse", 1.35942),
            c(17, "r2", 0.0612526),
            c(17, "mae", 0.981016),
            c(17, "rmse", 1.31713),
            c(18, "r2", -0.0603866),
            c(18, "mae", 1.09242),
            c(18, "rmse", 1.39986),
            c(19, "r2", 0.163452),
            c(19, "mae", 0.91398),
            c(19, "rmse", 1.24336),
        ],
    ),
    e(
        33,
        "first result table has six supported RMSE outcomes",
        (38, 41),
        [
            c(40, "rmse", 32.7321),
            c(40, "rmse", 3.191),
            c(40, "rmse", 3.1931),
            c(41, "rmse", 15.262),
            c(41, "rmse", 4.8028),
            c(41, "rmse", 4.8054),
        ],
    ),
    x(34, "smoke report contains no block with three supported empirical outcomes"),
    x(35, "qualitative attach report contains no block with three supported quantitative outcomes"),
    e(
        36,
        "core-results table has eight supported accuracy, AP, and FPS outcomes",
        (29, 32),
        [
            c(31, "accuracy", 0.9372),
            c(31, "ap", 0.9828),
            c(31, "frames_per_second", 10.13),
            c(31, "frames_per_second", 34.18),
            c(32, "accuracy", 0.9266),
            c(32, "ap", 0.9779),
            c(32, "frames_per_second", 23.85),
            c(32, "frames_per_second", 43.35),
        ],
    ),
    e(
        37,
        "first contiguous training-results section has eight supported test-accuracy outcomes",
        (3, 34),
        [
            c(5, "accuracy", 0.38),
            c(9, "accuracy", 0.333),
            c(13, "accuracy", 0.36),
            c(17, "accuracy", 0.375),
            c(21, "accuracy", 0.406),
            c(25, "accuracy", 0.414),
            c(29, "accuracy", 0.415),
            c(34, "accuracy", 0.375),
        ],
    ),
]


def main() -> None:
    sample = json.loads((ROOT / "sample.json").read_text())
    by_rank = {item["sample_rank"]: item for item in sample["samples"]}
    labels = []
    for case in CASES:
        item = by_rank[case["rank"]]
        labels.append(
            {**case, "repository": item["repository"], "source_file": item["source_file"]}
        )
    eligible = [case for case in labels if case["eligible"]]
    if len(eligible) != 30 or eligible[-1]["rank"] != 37:
        raise SystemExit("v15 annotation stop invariant failed")
    payload = {
        "schema_version": "reprocheck.cross-project-labels.v15",
        "annotation_method": "blind source-only manual annotation; extractor output not consulted",
        "reviewed_documents": 37,
        "eligible_documents": 30,
        "selected_claims": sum(len(case["claims"]) for case in eligible),
        "labels": labels,
    }
    (ROOT / "labels.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
