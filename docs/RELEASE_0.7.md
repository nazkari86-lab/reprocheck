# ReproCheck 0.7.0

Version 0.7 is a narrow post-holdout parser correction. It does not replace or
rescore the immutable v0.6 preregistered zero-shot result.

## Change

- AP-small, AP-medium, and AP-large table columns, including abbreviated
  `AP S`, `AP M`, and `AP L` headers, are no longer collapsed into generic AP.
- AP, AP50, AP75, AP50-95, and scoped box/mask AP extraction remain supported.
- Markdown and HTML regression tests cover the corrected boundary.

## Evidence boundary

The v0.6 holdout revealed 51 genuine false positives caused by size-specific AP
over-extraction. Version 0.7 removes all 51 on that inspected corpus without
changing its other predictions. This is development evidence after holdout
inspection, not a new estimate of generalization. The frozen v0.6 primary score
remains 297 TP, 67 FP, and 16 FN.

The remaining 16 FP plus 16 FN under the strict frozen labels come from the
recorded annotation-category error in `yolo-world.md`: values under AP50 and
AP75 were labelled as AP. Against the post-hoc corrected categories, v0.7 has
313 TP, 0 FP, and 0 FN on the inspected corpus. That diagnostic must not be
presented as zero-shot accuracy.

## Regression gates

- Controlled benchmark: 12/12 behavioral cases and 3/3 malformed-input rejects.
- Frozen public study: 40/40 claims, 67/67 defects, and 63/63 controls.
- Frozen challenge: unchanged at 1,006 TP, 2 strict FP, and 0 FN.
- Unit tests: AP-size regression coverage for Markdown and HTML.

The next valid generalization claim requires a newly preregistered holdout whose
contents and labels are not inspected during v0.7 development.

The reproducible development artifact is checked by
`make holdout-development`. Its result carries `zero_shot: false` and preserves
the SHA-256 reference to the immutable v0.6 primary result.

## Subsequent zero-shot evaluation

After the v0.7 wheel was frozen, a second cross-domain holdout was preregistered
before source download. On 295 claims from timm, MMSegmentation, fairseq, and
PaddleClas, v0.7 produced 259 TP, 0 FP, and 36 FN: 100% observed precision and
87.80% recall. All mIoU and Accuracy claims were recovered; all misses were
standalone Top-1/Top-5 headers. `make holdout-v07` verifies and byte-identically
replays this primary result.
