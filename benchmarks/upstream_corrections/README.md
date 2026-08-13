# Natural upstream correction corpus

This benchmark freezes files immediately before and after 17 merged corrections
in public upstream repositories. Each pull request identifies a prior metric
value or label as wrong. ReproCheck does not inject any defect into this corpus.

The corpus contains 17 independent corrections and 56 selected corrected claims
from 12 repositories maintained by nine organizations:

- OpenMMLab: MMDetection, MMSegmentation, MMAction2, and MMDetection3D.
- Hugging Face: Transformers.
- OpenVINO: Open Model Zoo.
- Google: Uncertainty Baselines.
- PyG: PyTorch Frame.
- Sigstore: Model Transparency.
- Ponder, Alley, and Envio benchmark documentation.

The cases cover AP/AR, mIoU, Dice, AUC, F1, top-k accuracy, Waymo L1/L2 mAP and
mAPH, compound AUROC/AUPRC/accuracy fields, durations, and speedups in Markdown,
YAML, JSONL, prose, and standard COCO console output. The exact pull requests,
immutable file URLs, expected before/after values, and selected records are
declared in `manifest.json`.

Six corrections also reference immutable raw evidence. The benchmark parses the
evidence key or claim and verifies that it agrees with the corrected claim,
allowing only the declared display rounding. Another candidate log was rejected
because its recorded value did not support the corrected table value; it was not
silently counted as evidence.

The first 12 cases were found retrospectively. The five `discovery-v1` cases are
the complete accepted subset of one frozen 25-result GitHub query. The exact
query, timestamp, criteria, rank order, decision, and exclusion reason are stored
in `discovery_protocol.md` and `discovery_snapshot.json`; `verify_discovery.py`
checks that every result remains adjudicated and every inclusion is linked to
the manifest.

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
correction. Only six cases have usable immutable raw evidence; the other 11
prove the existence and parser coverage of real merged corrections, not
independent recomputation from predictions. The frozen search cohort reduces
discretionary selection within one query, but it is not a probability sample of
GitHub.

Controlled mutations remain useful as mechanism and negative-control tests
elsewhere in the repository. They are reported separately and must not be
described as natural-error evidence.
