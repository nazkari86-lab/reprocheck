# Upstream discovery v8: broad fresh zero-shot holdout

ReproCheck 0.23.0 is frozen at commit `6238f2c` before retrieval. This study
tests numeric result extraction from public merged pull requests owned by
organizations not exposed in upstream discovery v2-v7 or the retrospective
correction corpus.

Forty exact search frames are fixed in `retrieve.py`. The first 100 GitHub API
results per frame are deduplicated and deterministically ordered with a frozen
SHA-256 seed. At most 25 pull requests per frame are selected, with global caps
of one repository and one repository owner. The maximum sample is 1,000.

Every sampled pull request receives an eligibility label without importing or
running ReproCheck. An eligible case needs an immutable human-readable
before/after report artifact, a uniquely identifiable numeric result change,
and unchanged metric scope, system, dataset, and configuration. Pure version,
configuration, dataset, or experiment changes are excluded. Claim selection
must be completed from source diffs before the first parser execution.

Labels, selected cases, source snapshots, and SHA-256 locks must be committed
and pushed before evaluation. Complete-case visibility is primary; individual
claim visibility is secondary. Wilson 95% intervals, eligibility yield, file
formats, metric families, and owner breadth are reported separately. The
query-conditioned cohort is not a population estimate. A low or zero score is
a valid outcome and no post-result tuning may change the v8 zero-shot score.

