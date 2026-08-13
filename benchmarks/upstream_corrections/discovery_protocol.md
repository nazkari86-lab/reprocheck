# Frozen discovery protocol v1

This protocol was frozen before adding the five `discovery-v1` cases to the
natural upstream correction corpus.

## Retrieval

- Source: GitHub pull-request search.
- Retrieval time: `2026-08-13T10:38:30Z`.
- Exact query: `"fix benchmark numbers" in:title,body is:merged`.
- Requested limit: 100; the API returned 25 results.
- Frozen order and adjudication: `discovery_snapshot.json`.

## Inclusion criteria

Every search result was inspected in rank order. A result was included only if:

1. GitHub's pull-request API confirmed `merged_at` was non-null.
2. The PR explicitly described an earlier benchmark number as incorrect,
   inaccurate, stale, or in need of correction.
3. An immutable parent/merge pair contained an isolated human-readable numeric
   claim before and after the correction.
4. ReproCheck could parse the same semantic metric from both versions.
5. The evidence was not described as synthetic-only.
6. The correction was not a duplicate publication of the same underlying
   benchmark correction already selected from a higher-ranked result.

Application telemetry, code-only correctness bugs, new benchmarks without a
corrected prior claim, generated line-number changes, and bulk rewrites without
an isolated claim pair were excluded.

## Interpretation

This is a reproducible search cohort, not a probability sample of GitHub or of
all erroneous research claims. Query wording, GitHub ranking, public-repository
availability, and authors' willingness to say “fix benchmark numbers” all shape
the cohort. The protocol reduces cherry-picking within this one query; it does
not establish population recall or prevalence.
