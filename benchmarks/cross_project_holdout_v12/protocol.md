# Cross-project holdout v12 protocol

## Purpose

Estimate zero-shot recall and precision for quantitative empirical claims under
the frozen ReproCheck 0.26.0 extractor at commit `0b52ada`. No v12 source,
repository, label, case identifier, or numeric answer was inspected while that
extractor was developed.

## Prospective sampling

- Execute the 36 query frames in `retrieve.py` in their frozen order.
- Within every frame, order candidates by the frozen salted SHA-256 digest and
  select at most two documents.
- Exclude every repository and owner recorded in any discovery/sample artifact
  from upstream discovery v2-v9, upstream corrections, and cross-project
  holdouts v10-v11, including previously retrieved ineligible documents.
- Apply a global cap of one repository per owner.
- Save immutable API responses, blob SHAs, source bytes, and SHA-256 digests.
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
the inclusive block line range. Labels must be completed without importing,
executing, or viewing output from ReproCheck. Sources and labels are hashed,
committed, and pushed before the evaluator runs.

## Frozen evaluation

A gold claim is recalled only when the extractor returns the same source line,
canonical metric, and value within absolute tolerance `1e-9`. A predicted claim
inside the registered block is correct only when it matches a gold claim under
the same rule; unmatched predictions are false positives. Duplicate claims are
matched as a multiset. A document is completely visible when all gold claims
are recalled. Wilson score intervals use 95% confidence and
`z=1.959963984540054`.

Primary endpoint: micro claim recall. Confirmatory safety endpoint: micro claim
precision inside annotated blocks. Secondary endpoint: complete-document
visibility.

The preregistered success condition is all of:

1. at least 20 eligible documents from independent owners;
2. claim recall at least 85%;
3. lower 95% Wilson bound for recall at least 70%;
4. block precision at least 95%;
5. lower 95% Wilson bound for precision at least 90%;
6. complete-document visibility at least 75%.

Only the first evaluation from frozen ReproCheck 0.26.0 is zero-shot. Any code
change after inspecting v12 is development and cannot replace the result.

