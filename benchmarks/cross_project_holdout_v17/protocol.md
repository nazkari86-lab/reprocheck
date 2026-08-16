# Cross-project holdout v17 protocol

## Purpose and status

V17 is a prospective external validity study of the frozen ReproCheck 0.29.0
extractor at commit `00e14dd2d8b646dd12ed77e5833e891fb3ca634b`.  It is a new
study, not a re-score of v15 or the source-only screening work in v16.

V16 did not reach its minimum eligible-document count in the reviewed prefix:
many GitHub code-search hits were specifications, configuration templates, or
documents whose first result block was outside the public metric ontology.  V17
therefore tests the stated scope directly: public benchmark result blocks with
explicit canonical metric headers.  This change is documented before retrieval;
it does not modify the extractor.

## Prospective sampling

- Run the 30 exact query frames in `retrieve.py` in recorded order.
- Salt-sort each GitHub code-search response by SHA-256; keep at most three
  candidates per frame and no more than one repository per owner.
- Exclude every repository and owner in v13-v16, whether eligible or not.
- Store raw API responses, blob SHA, source bytes and SHA-256 before review.
- Review only increasing global sample rank. Stop after 30 eligible documents,
  or after all 90 candidate slots are exhausted.

## Eligibility and source-only labels

The eligible block is the first table or contiguous prose/console block with
3–20 explicit scalar measurements. Each measurement must name a canonical
metric in `../cross_project_holdout_v15/supported-ontology.json`, or occur in a
table whose row or column header unambiguously names that metric.

Do not label targets, thresholds, configuration values, denominators, ranges,
deltas, badges, status text, dates, citations, or image-only outputs.  Labels
are created from source files alone: the extractor must not run until sources,
labels, evaluator, and study lock are committed and pushed.

## Frozen evaluation and decision rule

Predictions are matched as multisets by source line, canonical metric, and
value rounded to 12 decimal places.  Report micro recall, micro precision,
Wilson 95% intervals, exact-document rate, eligible owner count, and every
exclusion.

V17 supports a high external-generalization claim only if all hold:

1. at least 20 eligible documents from 20 independent owners;
2. recall at least 85% and lower Wilson bound at least 70%;
3. precision at least 95% and lower Wilson bound at least 90%;
4. exact-document rate at least 75%.

Only the first evaluator execution after the lock is zero-shot.  Any later run
is development evidence and must not replace it.
