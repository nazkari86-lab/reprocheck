# Cross-project holdout v14 protocol

## Purpose

Estimate zero-shot recall and precision for quantitative empirical claims under
the frozen ReproCheck 0.27.0 extractor at commit
`f7fe35a20d55fa48ab35c388645557ac4804efaa`. V14 replaces only the exhausted
v13 search frame; it does not alter the extractor or success thresholds.

## Prospective sampling

- Execute the 30 new result-file query frames in `retrieve.py` in frozen order.
- Within every frame, order candidates by the frozen salted SHA-256 digest and
  select at most three documents.
- Exclude every repository and owner recorded in any discovery/sample/frame
  artifact from upstream discovery v2-v9, upstream corrections, and
  cross-project holdouts v10-v13, including all previously retrieved ineligible
  candidates.
- Apply a global cap of one repository per owner.
- Save raw API responses, blob SHAs, source bytes, and SHA-256 digests.
- Review only in ascending global sample rank. Stop at 25 eligible documents or
  after exhausting the sample. At least 20 eligible independent owners are
  required.

## Eligibility and annotation

A document is eligible when it is a public project result document whose first
principal empirical-result block contains 3-20 textual quantitative outcome
claims. A block is one table or one contiguous prose/console section. Package
metadata, badges, configuration examples, citations, input sizes without
outcomes, datasets, generated references, plans, and image-only results are
ineligible.

Annotate every quantitative empirical outcome in that first block, in reading
order, with exact line, canonical metric, and normalized numeric value. Record
the inclusive block line range. Apply the frozen v13 `metric-policy.json`
without consulting extractor output. Threshold/configuration columns are not
outcomes. Repeated outcomes remain repeated multiset members. Sources and
labels must be hashed, committed, and pushed before the evaluator runs.

## Frozen evaluation

A gold claim is recalled only when the extractor returns the same source line,
canonical metric, and value within absolute tolerance `1e-9`. A predicted claim
inside the registered block is correct only when it matches a gold claim under
the same rule; unmatched predictions are false positives. Duplicate claims are
matched as a multiset. A document is exact only when predicted and gold
multisets are equal. Wilson intervals use 95% confidence and
`z=1.959963984540054`.

The preregistered success condition is all of:

1. at least 20 eligible documents from independent owners;
2. micro claim recall at least 85%;
3. lower 95% Wilson bound for recall at least 70%;
4. micro block precision at least 95%;
5. lower 95% Wilson bound for precision at least 90%;
6. exact-document rate at least 75%.

Only the first evaluation from frozen ReproCheck 0.27.0 is zero-shot. Any code
change after inspecting v14 is development and cannot replace the result.
