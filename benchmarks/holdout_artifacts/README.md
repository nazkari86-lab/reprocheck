# Preregistered v0.6 zero-shot holdout

This directory is a new evaluation phase, separate from the 114-artifact
development challenge. `preregistration.json` was written before repository
commits, trees, or file contents were downloaded for this holdout and before
the frozen 0.6 evaluator was run.

The selection, annotation scope, matching rule, evaluator SHA-256, and decision
policy are locked. Any parser change after observing the result requires a new
version and cannot replace the preserved 0.6 zero-shot result.

## Frozen result

The selected corpus contains 25 complete files from four official repositories
at pinned commits. Fifteen files contain 313 in-scope AP, AP50, or AP75 table
claims. One internal reviewer checked the independent rule-based annotations
before the evaluator ran; there are no external annotators or adjudication.

| Measure | Frozen v0.6 zero-shot |
| --- | ---: |
| TP / FP / FN | 297 / 67 / 16 |
| Precision | 81.59% |
| Precision Wilson 95% | 77.29%-85.24% |
| Recall | 94.89% |
| Recall Wilson 95% | 91.86%-96.83% |
| Exact files, all 25 | 92.00% |
| Exact files with claims, 15 | 86.67% |

The evaluator was exact on 23/25 files, including the DETR, YOLOv5, and YOLOX
files. All strict errors occur in two Ultralytics documents. A post-output
internal review found that 16 FP plus 16 FN in `yolo-world.md` are frozen label
category errors: values under `mAP50` and `mAP75` were labelled as generic AP.
The remaining 51 FP in `yolov7.md` are genuine evaluator over-extractions of
size-specific AP-small, AP-medium, and AP-large columns excluded by the
registered scope. The strict score is not changed. The diagnostic-only score
after correcting only the annotation categories would be 313 TP, 51 FP, and 0
FN (85.99% precision, 100% recall).

## Verification

```bash
make holdout
make holdout-replay
```

`make holdout` checks source, annotation, runner, evaluator, result, and review
SHA-256 bindings plus the result schema and arithmetic. `make holdout-replay`
installs the frozen wheel without dependencies in a clean temporary environment
and requires byte-identical output. The immutable primary result SHA-256 is
`f87ac0c5c10f00c289bd4046ea0f67d07f26d4a5aba3dab74fa8f54fe935d83f`.

This holdout is stronger evidence than the earlier development challenge, but
it is not a universal accuracy estimate: the corpus is computer-vision-heavy,
three repositories are from the same organization, and annotation had one
internal reviewer. Independent dual annotation and blinded adjudication remain
necessary for a publication-grade general benchmark.

## Post-holdout v0.7 development result

After inspecting the v0.6 errors, version 0.7 was changed to reject
AP-small/medium/large columns. A separate post-hoc annotation artifact corrects
the 16 frozen AP/AP50/AP75 category mistakes without changing the primary v0.6
labels. Against that development-only artifact, v0.7 produces 313 TP, 0 FP, and
0 FN. This confirms the known failure was corrected; it does not measure
generalization.

```bash
make holdout-development
```

The target checks the non-zero-shot phase marker, schema, frozen v0.7 wheel,
post-hoc annotations, primary-result reference, result hashes, and a
byte-identical clean-environment replay. Any accuracy claim for v0.7 must use a
new holdout selected and labelled without inspecting its evaluator output.
