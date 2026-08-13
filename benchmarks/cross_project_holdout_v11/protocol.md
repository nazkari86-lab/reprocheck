# Cross-project holdout v11 protocol

## Purpose

Estimate zero-shot visibility of quantitative result claims under the frozen
ReproCheck 0.25.0 extractor. The evaluator is commit `792ad73`. No v11 source,
label, repository name, case identifier, or numeric answer was inspected while
that extractor was developed.

## Prospective sampling

- Execute the query frames in `retrieve.py` in their frozen order.
- Within every frame, order candidates by the frozen salted SHA-256 digest and
  select at most two.
- Exclude every repository and every owner exposed by upstream discovery v2-v9,
  upstream corrections, and all retrieved v10 samples, including ineligible or
  unevaluated v10 documents.
- Apply a global cap of one repository per owner.
- Save immutable API responses, blob SHAs, source bytes, and SHA-256 digests.
- Review samples only in global sample-rank order. Stop at 25 eligible documents
  or after exhausting the sample. At least 20 eligible documents are required.

## Eligibility and annotation

A document is eligible when it is a public project result document that reports
at least three quantitative empirical outcomes produced by a benchmark,
experiment, evaluation, or test run. Package metadata, badges, configuration
examples, citations, datasets without reported project outcomes, generated API
references, and documents consisting only of plans are ineligible.

For every eligible document, select the first principal result block in reading
order. A block is one table or one contiguous prose/console section. Annotate up
to 12 quantitative outcome claims from that block, in reading order, using the
canonical metric vocabulary. Labels must be completed without importing or
executing ReproCheck. Source and label hashes are then committed and pushed
before the evaluator is run.

## Frozen evaluation

A selected claim is visible only when the extractor returns the same source
line, canonical metric, and numeric value within absolute tolerance `1e-9`.
A document is completely visible only when every selected claim is visible.
Wilson score intervals use 95% confidence and `z=1.959963984540054`.

Primary endpoint: selected-claim visibility. Secondary endpoint: complete
document visibility.

The preregistered success condition is all of:

1. at least 20 eligible documents from independent owners;
2. claim visibility at least 85%;
3. lower 95% Wilson bound for claim visibility at least 70%;
4. complete-document visibility at least 75%.

Only the first evaluation from the frozen 0.25.0 commit is zero-shot. Any code
change after inspecting v11 is development and cannot replace that result.

