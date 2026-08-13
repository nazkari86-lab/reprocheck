# ReproCheck 0.22.0

Version 0.22.0 expands claim extraction after a preregistered real-world failure.

- Frozen source-unseen v5 evaluation: 0/11 complete cases, 0/34 selected claims.
- Post-inspection development evaluation: 11/11 cases, 34/34 claims.
- Added Markdown-decoration handling while preserving raw source text.
- Added row-labeled rates and ratios, scaled throughput, memory comparisons,
  postfix/range speedups, embedded table durations, latency aliases, and numeric TSV.
- Added regression tests and a checksum-verifying v5 gate.

The development result is intentionally not described as an independent validation.
The study uses only immutable public pull-request sources, but remains query-conditioned.
