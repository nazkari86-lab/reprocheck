# Cross-project holdout v18 protocol

V18 is a prospective test of ReproCheck 0.29.0 at commit
`00e14dd2d8b646dd12ed77e5833e891fb3ca634b`. It follows the failed-to-retrieve
v17 attempt and is registered before any v18 query is executed.

The fixed queries target publicly reported result documents using one canonical
metric family at a time. This avoids v17's zero-hit triple-conjunction queries,
while retaining the same owner cap, prior-study exclusions, source preservation,
and source-only annotation rule.

For each query, salt-sort GitHub code-search results, keep at most three files,
and allow no more than one repository per owner globally. Exclude all owners and
repositories in v13-v17. Store raw responses, source blobs, and hashes before
review. Review by increasing rank and stop at 30 eligible documents or after
90 slots.

An eligible first result block has 3–20 scalar measurements with canonical
metrics in `../cross_project_holdout_v15/supported-ontology.json`. Exclude
targets, thresholds, configurations, deltas, ranges, status labels, and
image-only outputs. Do not execute the extractor until source-only labels,
evaluator, and study lock are committed and pushed.

Success requires 20 independent eligible owners, recall >=85% with Wilson lower
bound >=70%, precision >=95% with lower bound >=90%, and exact-document rate
>=75%. Only the first locked evaluator execution is zero-shot.
