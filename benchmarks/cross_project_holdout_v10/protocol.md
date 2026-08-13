# Cross-project holdout v10: preregistered ReproCheck 0.24.0 evaluation

ReproCheck 0.24.0 is frozen at tag `v0.24.0`, commit
`734a3d5b4ec421bcccacede69df4f86f7c1900fe`, before retrieval. No extractor
change is permitted after retrieval begins.

## Target and sampling

The target is visibility of empirical numeric result claims in public Markdown
documents from previously unseen open-source repository owners. Twenty-four
exact GitHub code-search frames are frozen in `retrieve.py`. Results are ordered
by a SHA-256 digest of the immutable blob identity and a fixed seed. At most two
documents are selected per frame, with global caps of one document per
repository and one repository per owner. Repositories and owners exposed in
upstream discovery v2-v9 or the retrospective correction corpus are excluded.

The intended evaluation size is the first 20 eligible documents. Retrieval may
select up to 48 documents so eligibility can be established without running
ReproCheck. If fewer than 15 eligible documents exist, the study reports the
shortfall and does not claim a 9/10 external-generalization result.

## Eligibility and annotation

A document is eligible when its immutable sampled blob contains at least one
human-readable empirical numeric result produced by an evaluation, test, or
benchmark. Configuration values, prices, dates, versions, installation steps,
badges, hardware specifications, dataset sizes without a measured outcome, and
future/illustrative targets are excluded.

Without importing or executing ReproCheck, the reviewer records every in-scope
claim in the document's principal results table or principal results paragraph.
If that region contains more than twelve claims, the first twelve in source
order are selected. Claim identity includes normalized metric, numeric value,
and source line. Labels, source blobs, eligibility decisions, and SHA-256 locks
must be committed and pushed before the first extractor execution.

## Endpoints

The primary endpoint is complete-document visibility: every selected claim in
an eligible document must be extracted. Claim visibility is secondary. The
study reports Wilson 95% confidence intervals, eligible yield, independent
owner count, metric-family breadth, and document-structure breadth.

Success requires at least 15 eligible independent owners, at least 85% claim
visibility, and a Wilson 95% lower bound of at least 70%. A 9/10 external-
generalization claim additionally requires at least 85% complete-document
visibility. Results remain reportable if these thresholds are missed. No
post-result code change can alter the frozen v10 score.
