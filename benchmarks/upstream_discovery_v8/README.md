# Upstream discovery v8

This is a preregistered, source-unseen evaluation of ReproCheck 0.23.0 at
commit `6238f2c`. It contains only public, real GitHub pull-request artifacts;
no synthetic cases or generated claim text are used.

The deterministic search sampled 994 merged pull requests from 994 independent
repository owners across 40 frozen query frames. Human semantic review labeled
all 994 records before the parser's first execution. Sixteen same-scope numeric
corrections from sixteen owners were eligible, contributing 24 selected claims.

`details.json.gz` is the lossless compressed collection record. Decompress it
with `gzip -dk details.json.gz` only when rebuilding `review_packet.json`,
`labels.json`, or source snapshots. `study.lock.json` freezes all evaluator
inputs and `sources.lock.json` pins every immutable before/after source by
SHA-256. Run `verify_study.py` before evaluation.

The primary endpoint is complete-case visibility: a case passes only when every
selected before and after claim is extracted. Claim visibility is secondary.
Wilson 95% intervals are reported for both. This query-conditioned cohort is
not a population estimate.
