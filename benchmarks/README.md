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
with `baseline-v0.16.0.json` rather than accepting a console success message.

## Expanded integrity and robustness experiments

Run `make expanded-experiments` for four separately scoped studies:

- nine certificate/graph/signature mutation families at three attacker levels;
- eight corruptions derived from Iris, Diabetes, and YOLO artifacts plus three
  clean controls;
- thirteen declared numerical representation cases;
- five end-to-end repeats at 10, 100, and 1,000 report claims.

The protocol and runner files were committed before the first recorded results
and are protected by `experiment-design-v1.lock.json`. Exact deterministic
results and the timing-free scalability projection are protected by
`expanded-results-v1.lock.json`. See `docs/EXPANDED_EXPERIMENTS.md` for results
and the important unsigned full-rehash boundary.

## Controlled lexical near-duplicates

Run `make near-duplicate-benchmark` to evaluate the legacy token Jaccard method
and both `hybrid_lexical_v1` and `ordered_tokens_v1` on 12 controlled English,
Russian, and Kazakh lexical
mutations plus 12 unrelated controls. At threshold 0.8, the frozen v1 result is
100% precision and 100% recall for the hybrid method versus 100% precision and
25% recall for token Jaccard. The cases and their SHA-256-bound baseline are in
`near_duplicate/`.

This small synthetic benchmark isolates typo, punctuation, word-boundary,
inflection, insertion, and reordering behavior. It is not evidence of semantic
paraphrase accuracy or natural-corpus prevalence.

## Indexed-search scalability

Run `make text-index-benchmark` to compare deterministic pair counts with a
naive exhaustive join. On the 10,000-by-1,000 sparse corpus, the complete index
reduces 10,000,000 possible pairs to 51,548 candidates and 500 expensive
ordered-sequence scores. On a deliberately adverse corpus where every row
shares one token, candidate reduction falls to zero, but the multiset upper
bound still reduces 400,000 sequence scores to 100. Exact result equivalence is
checked against exhaustive search on 30,000 pairs. These synthetic counts prove
index mechanics, not natural-corpus latency.

## Preregistered PAWS holdout

The English PAWS-Wiki study under `paws_leakage/` separates an 8000-pair
validation phase from an 8000-pair locked test. Methods, thresholds, evaluator,
source hashes, primary hypothesis, and statistics were committed before the
test content was downloaded. On the unseen test, `ordered_tokens_v1` reaches
70.53% balanced accuracy versus 54.94% for `hybrid_lexical_v1` (+15.58
percentage points; exact McNemar `p = 7.07e-143`). This validates sensitivity
to meaning-changing word order, but does not establish multilingual or general
semantic-duplication accuracy.

## Frozen public artifacts

Run the pinned 60-file study with:

```bash
make study
```

This verifies the source manifest and annotations, writes the raw schema-checked
study input/output path, and compares all deterministic results with
`real_artifacts/baseline-v6.json`. It measures 40 annotated numerical claims,
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
