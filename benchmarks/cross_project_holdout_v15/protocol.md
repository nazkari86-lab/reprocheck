# Cross-project holdout v15 protocol

## Purpose

Estimate fresh zero-shot visibility and block precision for the frozen
ReproCheck 0.28.0 extractor at commit
`76614583ae8676ba6ed309b43ca8865e707d8c4e`. V15 evaluates the published
supported ontology rather than inventing source-specific metric identifiers.

## Prospective sampling

- Execute the 30 query frames in `retrieve.py` in frozen order.
- Salt-sort each frame by SHA-256 and select at most three documents.
- Exclude every repository and owner present in v2-v14 artifacts, including
  previously retrieved ineligible candidates. Cap the sample at one repository
  per owner.
- Save raw API responses, blob SHAs, source bytes, and SHA-256 digests.
- Review documents only by ascending global rank and stop at 30 eligible
  documents or sample exhaustion. At least 20 independent eligible owners are
  required.

## Eligibility and annotation

The first principal empirical-result block is the first table or contiguous
prose/console section that contains at least three and at most twenty printed
outcomes whose canonical identifiers occur in `supported-ontology.json`.
Annotate every supported outcome in that block, including repetitions, using
the public 0.28 normalization contract. Unsupported numeric outcomes are
outside this study and are neither gold claims nor false positives. Targets,
thresholds, inputs, configuration values, dates, citations, badges, plans,
package metadata, and image-only results are not outcomes.

Annotation must be performed from source text without running or consulting
extractor output. Sources, labels, and their study lock must be committed and
pushed before the first evaluator execution.

## Frozen evaluation

Within each locked block, filter predictions to identifiers in the frozen
ontology. Match gold and predicted claims as multisets by exact source line,
canonical identifier, and value rounded to 12 decimals. Report micro recall,
micro precision, Wilson 95% intervals, and exact-document rate.

Success requires all of:

1. at least 20 independent eligible owners;
2. recall at least 85% and its Wilson lower bound at least 70%;
3. precision at least 95% and its Wilson lower bound at least 90%;
4. exact-document rate at least 75%.

Only the first evaluation with frozen 0.28.0 is zero-shot. Later changes are
development and cannot replace it.
