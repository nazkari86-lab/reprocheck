# ReproCheck 0.24.0

Version 0.24.0 generalizes numeric-claim extraction from the preregistered v8
upstream discovery study. The frozen 0.23.0 evaluator reached 7/16 complete
cases and 9/24 claims on 16 independent repository owners. After inspection,
0.24.0 reaches 16/16 and 24/24 on the same cases; this is development evidence,
not a replacement for the zero-shot result.

The extractor now supports abbreviated P@k/R@k table headers, approximate
duration cells, wrapped and multilingual test-count prose, passed/skipped test
summaries, Metric/Value rows with machine-readable `_pct`/`_count` names, and
peak GPU VRAM statements. The rules contain no repository names, case IDs, or
holdout-specific numeric constants.

Fresh external validation must use a newly preregistered source-unseen cohort.
