# Upstream discovery v9: fresh post-0.24 zero-shot holdout

ReproCheck 0.24.0 is frozen at commit `2eff4e8` before retrieval. This study
tests numeric result extraction from public merged pull requests not exposed in
upstream discovery v2-v8 or the retrospective correction corpus.

The forty exact v8 search frames are reused with a new SHA-256 ordering seed.
Every previously exposed pull request and repository owner is excluded. The
first 100 GitHub API results per frame are deduplicated; at most 25 pull
requests per frame are selected, with global caps of one repository and one
owner. The maximum sample is 1,000.

Every sampled pull request receives an eligibility label without importing or
running ReproCheck. Eligibility requires an immutable human-readable
before/after artifact, a uniquely identifiable empirical numeric result change,
and unchanged metric scope, system, dataset, and configuration. New versions,
datasets, configurations, or experiments are excluded. Claims and source locks
must be committed and pushed before the first parser execution.

Complete-case visibility is primary; claim visibility is secondary. Wilson 95%
intervals, eligibility yield, owner breadth, source structures, and metric
families are reported. This query-conditioned cohort is not a population
estimate. No post-result tuning can alter the v9 zero-shot score.
