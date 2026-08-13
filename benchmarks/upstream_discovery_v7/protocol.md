# Upstream discovery v7: fresh documentation-sync holdout

ReproCheck 0.22.0 is frozen at commit `901352b` before retrieval. This holdout
tests numeric benchmark/report corrections in public merged pull requests from owners
not exposed in v2-v6 or the retrospective corpus.

Eight exact queries are fixed in `retrieve.py`. The first 100 API results per query are
deduplicated, ordered with a fixed SHA-256 seed, and sampled with global one-owner and
one-repository caps. At most 20 pull requests per frame are selected (maximum 160).

Without running or importing ReproCheck, every selected pull request must receive an
eligibility label. Eligible claims require an immutable human-readable before/after
artifact, a unique snippet, an explicit empirical numeric result, and unchanged metric,
system, dataset, and configuration. New experiments, versions, datasets, and
configurations are excluded. Labels, cases, sources, and their hashes must be committed
and pushed before the first parser run.

Primary endpoint is complete-case visibility; claim visibility is secondary. Counts,
Wilson 95% intervals, eligibility yield, and owner breadth are reported separately.
The query-conditioned cohort is not a population estimate. No post-result tuning is
allowed in v7, and a zero-eligible sample remains a valid result.
