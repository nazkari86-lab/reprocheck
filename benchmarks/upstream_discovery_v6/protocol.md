# Upstream discovery v6: fresh post-freeze holdout

## Objective

Test ReproCheck 0.22.0 on public numeric result corrections from repository owners
not present in the prior upstream studies. The extractor is frozen at commit
`5fdb6a6`. No extractor change is permitted after retrieval begins.

## Sampling

Six new GitHub search frames are fixed in `retrieve.py`. Each query requests the
first 100 merged pull requests created since 2024-01-01. Every pull request exposed
by v2-v5 or the retrospective correction corpus is excluded. Candidates are ordered
by a fixed SHA-256 seed. At most 15 are selected per frame, with a global cap of one
repository and owner. Maximum sample size: 90.

## Blind eligibility

ReproCheck output must not be generated until all sampled pull requests receive an
eligibility label and every eligible before/after snippet, metric, value, and context
is immutable. Eligibility is identical to v5: a human-readable report must correct
an explicit empirical number for the same system, data, configuration, and metric;
new experiments, configurations, versions, and datasets are excluded.

## Endpoints and boundary

Primary endpoint is complete-case visibility; claim visibility is secondary. Report
case and claim counts and Wilson 95% intervals separately. This is a small,
query-conditioned holdout, not a population estimate. A zero-eligible sample is a
valid yield result and must not be replaced. No post-result parser tuning is allowed
inside this study.
