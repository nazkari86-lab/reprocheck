# Benchmarks

## Controlled defects

Run with:

```bash
reprocheck benchmark --output outputs/benchmark.json
```

The benchmark creates 12 temporary projects with known ground truth, including
metric mismatch, evidence conflict, exact/normalized/group/near overlap,
unsafe notebook usage, missing claims, detection mismatch, and the distinction
between reported support and recomputation. Three additional malformed-input
cases must fail closed. Classification, regression, and detection recomputation
are all represented.

It measures finding precision/recall, case-level exact match, certificate
integrity, tamper detection, and invalid-input rejection.

The checked-in per-release baseline is a deterministic smoke benchmark, not
evidence of real-world accuracy. CI compares the complete deterministic summary
with `baseline-v0.9.0.json` rather than accepting a console success message.

## Frozen public artifacts

Run the pinned 60-file study with:

```bash
make study
```

This verifies the source manifest and annotations, writes the raw schema-checked
study input/output path, and compares all deterministic results with
`real_artifacts/baseline-v3.json`. It measures 40 annotated numerical claims,
7 internally labelled notebooks, 67 defective real-file mutations, and 63
semantically equivalent negative controls. Results are reported overall and by
source repository against both a naive inline regex and a stronger format-aware
baseline. Environment-dependent latency is intentionally excluded from the
frozen baseline.

The public corpus is stronger than synthetic-only evidence, but it is still not
an independent expert benchmark: 30 labels are rule-derived and the remaining
claim/notebook labels have one internal reviewer. Independent dual annotation
and adjudication remain future work.

## Frozen format challenge

Run the 114-artifact Detectron2/MMDetection checks with:

```bash
make challenge
make challenge-replay
```

The immutable zero-shot 0.5 wheel recovered 18/1,006 frozen table labels. The
post-inspection 0.6 wheel recovered 1,006/1,006 with two strict false positives
that a separate post-hoc internal review identifies as annotation omissions.
The original result, scoped replay, adapted result, evaluator wheels, schemas,
source SHA-256 manifest, and explicit validity limits are under
`challenge_artifacts/`. The 0.6 result is development evidence, not a held-out
generalization estimate.

## Preregistered v0.6 holdout

Run the unseen four-repository holdout checks with:

```bash
make holdout
make holdout-replay
```

The frozen v0.6 wheel extracted 297 TP with 67 FP and 16 FN from 313 registered
AP-family claims: 81.59% precision and 94.89% recall. It was exact on 23/25
files. A separately stored post-hoc review attributes 16 FP plus 16 FN to a
frozen annotation category error and 51 FP to genuine size-specific AP
over-extraction. Primary metrics remain unchanged. All inputs, the one-shot
runner, evaluator wheel, output, and review are hash-locked, schema-checked, and
byte-identically replayed from a clean environment under `holdout_artifacts/`.
Version 0.7 removes the 51 genuine AP-size false positives on this inspected
corpus; that post-holdout result is development evidence only.

## Preregistered v0.7 cross-domain holdout

`make holdout-v07` verifies and byte-identically replays a second unseen corpus:
39 files, four repositories, and 295 mIoU/Accuracy/Top-1/Top-5 claims. The frozen
v0.7 result is 259 TP, 0 FP, and 36 FN, or 100% observed precision and 87.80%
recall. All 36 misses are standalone Top-1/Top-5 headers. The immutable protocol,
sources, labels, result, schema, post-hoc review, and runner are stored under
`holdout_v07_artifacts/`.
Version 0.8 recovers 295/295 on this inspected corpus after adding standalone
Top-K headers; that adapted result is stored separately as development evidence.

External evidence bundles complement the injected-defect suite:

- `external/yolo26n-coco8` compares independently recomputed detection AP with
  official Ultralytics metrics.
- `external/sklearn-tabular` compares classification and regression metrics
  with scikit-learn on Iris and Diabetes and audits the frozen split IDs.
