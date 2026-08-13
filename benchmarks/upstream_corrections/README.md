# Natural upstream correction corpus

This benchmark freezes files immediately before and after 12 merged corrections
in public upstream repositories. Each pull request identifies a prior metric
value or label as wrong. ReproCheck does not inject any defect into this corpus.

The corpus contains 12 independent corrections and 38 selected corrected claims
from seven repositories maintained by four organizations:

- OpenMMLab: MMDetection, MMSegmentation, MMAction2, and MMDetection3D.
- Hugging Face: Transformers.
- OpenVINO: Open Model Zoo.
- Google: Uncertainty Baselines.

The cases cover AP/AR, mIoU, Dice, AUC, F1, top-k accuracy, Waymo L1/L2 mAP and
mAPH, and compound AUROC/AUPRC/accuracy fields in Markdown, YAML, and standard
COCO console output. The exact pull requests, immutable file URLs, expected
before/after values, and selected records are declared in `manifest.json`.

Five corrections also reference immutable raw evaluation logs. The benchmark
parses the log's evidence key and verifies that it agrees with the corrected
claim, allowing only the declared display rounding. A sixth candidate log was
rejected because its recorded value did not support the corrected table value;
it was not silently counted as evidence.

Run `make upstream-corrections`. The fetch step uses immutable commit URLs;
`sources.lock.json` records every URL and SHA-256 hash. The benchmark fails on:

- changed or missing source material;
- absence of the defect in the pre-fix file;
- absence of the correction in the post-fix file;
- failure of ReproCheck's parser to recover the expected metric and value; or
- disagreement between a corrected claim and its declared raw log evidence.

## Boundary

This is a curated historical-correction corpus, not a random sample and not an
estimate of recall across all software-repository defects. Multiple records
changed by one pull request are correlated and count as one independent
correction. Only five cases have usable immutable raw logs; the other seven prove
the existence and parser coverage of real merged corrections, not independent
recomputation from predictions.

Controlled mutations remain useful as mechanism and negative-control tests
elsewhere in the repository. They are reported separately and must not be
described as natural-error evidence.
