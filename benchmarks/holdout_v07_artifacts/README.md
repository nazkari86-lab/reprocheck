# Preregistered v0.7 cross-domain holdout

This is an immutable zero-shot evaluation of the frozen ReproCheck 0.7 wheel.
The protocol, four repositories, commits, hash-ranked path sampling, metric
scope, and evaluator SHA-256 were registered before source contents were
downloaded. Sources and independent annotations were then locked before the
one-shot evaluator run.

## Corpus

- 39 complete Markdown files from timm, MMSegmentation, fairseq, and PaddleClas.
- 16 claim-bearing files with 295 registered table claims.
- 249 mIoU, 21 Top-1, 21 Top-5, and 4 Accuracy claims.
- One internal annotation reviewer, zero external reviewers, no adjudication.

The registered sampling found only one matching timm file, so the realized
corpus has 39 rather than the maximum possible 51 artifacts. No replacement
was selected based on content.

## Primary result

| Measure | Frozen v0.7 zero-shot |
| --- | ---: |
| TP / FP / FN | 259 / 0 / 36 |
| Precision | 100.00% |
| Precision Wilson 95% | 98.54%-100% |
| Recall | 87.80% |
| Recall Wilson 95% | 83.57%-91.05% |
| Exact artifacts, all 39 | 92.31% |
| Exact claim-bearing artifacts, 16 | 81.25% |

ReproCheck recovered all 249 mIoU and all 4 Accuracy claims with no false
positives. It recovered 3/21 Top-1 and 3/21 Top-5 claims. All 36 false negatives
come from standalone `top1`, `top5`, `Top-1 (%)`, and `Top-5 (%)` headers that
v0.7 does not recognize unless an `accuracy` token is also present. Post-hoc
review identified no annotation errors; the primary result remains unchanged.

## Reproduction

```bash
make holdout-v07
```

This verifies preregistration and evaluator locks, all source hashes, the
deterministic independent annotation output, JSON Schema, exact primary result,
post-hoc accounting, and byte-identical replay from the frozen wheel in a clean
temporary environment.

This is stronger generalization evidence than the earlier Ultralytics-heavy
holdout, but it is still table-only, dominated by mIoU claims, and internally
annotated. Any Top-1/Top-5 fix is development work for v0.8 or later and needs a
new unseen holdout before making another generalization claim.
