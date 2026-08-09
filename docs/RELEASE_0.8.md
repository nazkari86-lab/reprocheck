# ReproCheck 0.8.0

Version 0.8 is a narrow post-holdout correction for standalone Top-1 and Top-5
table headers. It preserves every frozen v0.5-v0.7 primary result.

## Change

- Recognize `top1`, `top5`, `Top-1 (%)`, and `Top-5 (%)` as Top-1/Top-5
  accuracy headers without requiring a neighboring `accuracy` token.
- Continue rejecting `Top-1 error`, `Top-5 error`, and abbreviated `err`
  variants because error rate is not accuracy and cannot be copied unchanged.
- Preserve the v0.7 exclusion of AP-small/AP-medium/AP-large columns.
- Add Markdown and HTML positive tests plus explicit error-rate negative tests.

## Evidence boundary

The frozen v0.7 cross-domain zero-shot result remains 259 TP, 0 FP, and 36 FN.
Those 36 misses revealed the Top-K header gap. After inspection, v0.8 recovers
all 295 frozen labels with 0 FP and 0 FN. This verifies correction on the known
corpus but is development evidence, not a new generalization estimate.

The v0.8 development evaluator, result, and replay are frozen separately from
the v0.7 primary result. A future generalization claim requires another unseen
holdout selected before v0.8 output is observed.

## Regression gates

- 147 unit/integration tests.
- Controlled benchmark: 12/12 behavioral cases and 3/3 malformed-input rejects.
- Frozen public study: 40/40 claims, 67/67 defects, and 63/63 controls.
- Frozen challenge behavior unchanged.
- Both prior zero-shot studies remain byte-identically replayable from their
  original wheels.
