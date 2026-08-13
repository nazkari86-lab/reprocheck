# Cross-project holdout v16 protocol

## Purpose

Estimate fresh zero-shot visibility and block precision for the public
ReproCheck 0.29.0 extractor at commit
`00e14dd2d8b646dd12ed77e5833e891fb3ca634b`. V16 is a new study, not a
recalculation of v15. It uses new query frames, repositories, owners, source
bytes, source annotations and a frozen evaluator.

## Prospective sampling

- Run the 30 frames in `retrieve.py` in their recorded order.
- Salt-sort every GitHub code-search result by SHA-256; retain at most three
  candidates per frame and no more than one repository per owner.
- Exclude every repository and owner present in v2-v15 artefacts, including
  candidates previously found ineligible.
- Store raw API responses, immutable blob SHAs, source bytes and SHA-256
  digests before reviewing any document.
- Review only increasing global sample rank. Stop at 30 eligible documents or
  after exhausting the 90-candidate frame. At least 20 independent owners are
  required.

## Eligibility and source-only annotation

The eligible block is the first table or contiguous prose/console result block
with 3–20 explicit, scalar measurements whose canonical identifier occurs in
`../cross_project_holdout_v15/supported-ontology.json`. A measurement must
state its metric or be in a table whose row/column header states it. Repeated
measurements count separately.

Do not annotate targets, thresholds, input sizes, table deltas, status labels,
denominators, ranges/bounds, dates, citations, configuration, plans, badges,
or image-only outputs. Annotation is source-only: do not execute or inspect the
extractor until source files and labels are locked and pushed.

## Frozen evaluation

Within each locked block, predictions are limited to the frozen ontology and
matched as multisets by source line, canonical metric and value rounded to 12
decimal places. Report micro recall, micro precision, Wilson 95% intervals and
exact-document rate.

Success requires all of:

1. at least 20 independent eligible owners;
2. recall at least 85% and lower Wilson bound at least 70%;
3. precision at least 95% and lower Wilson bound at least 90%;
4. exact-document rate at least 75%.

Only the first execution of the evaluator against its locked sources and labels
is zero-shot. Any later run is development evidence only.
