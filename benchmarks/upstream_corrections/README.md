# Natural upstream correction corpus

This benchmark freezes files immediately before and after three merged corrections in public upstream repositories. Each pull request explicitly calls the prior value or metric label erroneous. No defect is injected by ReproCheck.

The corpus contains three independent corrections affecting fourteen records:

- MMDetection FPG box AP: `49.6` corrected to `39.6` ([PR 9041](https://github.com/open-mmlab/mmdetection/pull/9041)).
- MMDetection Conditional DETR box AP: `40.9` corrected to `41.1` ([PR 9889](https://github.com/open-mmlab/mmdetection/pull/9889)).
- MMSegmentation UNet metadata: twelve `mIoU` labels corrected to `Dice` ([PR 1041](https://github.com/open-mmlab/mmsegmentation/pull/1041)).

Run `make upstream-corrections`. The fetch step uses immutable commit URLs; `sources.lock.json` records the resulting SHA-256 hashes. The benchmark rejects a changed source, a missing pre-fix defect, a missing post-fix correction, or a correction that ReproCheck's claim parser cannot extract with the expected metric name and value.

## Boundary

This is a real historical-correction corpus, not an estimate of recall on all software-repository defects. The twelve records changed by PR 1041 are correlated and count as one independent correction. Controlled mutations remain useful only as mechanism tests elsewhere in the repository and must not be described as natural evidence.
