# ReproCheck scientific protocol

## Research questions

1. On a frozen corpus of complete public ML artifacts, how accurately does a
   deterministic parser recover supported numerical claims relative to declared
   annotations, a fixed naive inline-regex baseline, and a stronger
   format-aware baseline?
2. When a numerical value in a real report is deliberately changed, does the
   evidence-tracing audit detect disagreement with the original metric record?
3. Under explicitly declared input contracts, which claim, metric, split, and
   certificate properties are deterministic and independently recheckable?
4. How much detection-table format coverage does a frozen evaluator retain on
   repositories selected before zero-shot evaluation, and what changes after
   the resulting failures become development data?

This version does not claim superiority to human review. No timed human-review
experiment has been run.

## Supported claims

ReproCheck supports classification, segmentation, detection, and generic
numeric claims in text, Markdown and HTML tables, notebooks, and structured
JSON. A table-only API preserves scoped AP/AR/PQ metric families and rejects
cells containing multiple candidate numbers instead of selecting one silently.
Classification metrics can be recomputed with binary, macro, or weighted
averaging. Detection AP is recomputed from raw boxes. Segmentation metrics can
be traced to selected benchmark records.

`supported` means that a claim agrees with a supplied metric table. `verified`
is reserved for a metric recomputed from predictions or detection boxes. A
claim matches when its absolute difference from evidence is no greater than
the declared tolerance. Conflicting evidence sources are always reported.

Numeric `y_true,y_pred` evidence in regression mode produces MAE, RMSE, and R2.
Constant-target R2 follows the finite convention: 1 for exact predictions and
0 otherwise. Binary classification mode also emits hard Dice and hard IoU for
the declared positive label.

Binary precision/recall/F1/Dice/IoU require an explicit positive label. Without
one, `auto` uses macro averaging even for two labels rather than guessing from
lexicographic order. An optional `y_score` column adds exact AUROC, threshold-
grouped AUPRC, Brier score, and log-loss clipped at machine epsilon; it requires an
explicit positive label and both outcome classes.

Markdown and HTML table claims retain recognized model/dataset/split/experiment
context. A wide-CSV selector such as `model=proposed` scopes its observations;
claims with a conflicting shared context are marked `no_evidence`. This is a
bounded deterministic ClaimKey, not general document understanding or support
for multiple evidence contexts inside one audit invocation.

A reproduced number can still support a bad hypothesis. These statuses do not
establish that a metric is appropriate, a hypothesis is true, or an experiment
generalizes to deployment data.

## Leakage guarantees

Given two CSV files and an ordered list of identity columns, ReproCheck computes
SHA-256 fingerprints of canonical row projections. Exact-overlap detection is
complete for byte-decoded field values in those columns. Normalized-overlap
detection is complete under Unicode NFKC, trim, case-fold, and whitespace
collapse.

If a group column is declared, every non-empty group value shared by train and
test is reported. The system makes no claim that undeclared identities, visual
near-duplicates, or causal leakage are absent. The default
`hybrid_lexical_v1` text score is the maximum of token-set Jaccard and Unicode
character-trigram Dice similarity. Candidate generation indexes every token
and trigram; size-only upper bounds remove a comparison only when neither score
can reach the declared threshold. Therefore indexed results equal exhaustive
pairwise evaluation for this score, but the score remains a lexical heuristic,
not a semantic certificate of absence. `token_jaccard` preserves the previous
method explicitly.

## Notebook boundary

Notebook analysis parses stored Python cells without executing them. Findings
are syntactic risk indicators. A test-named variable passed to `fit`, for
example, is suspicious but is not proof of leakage. `validation_data` and
`validation_split` arguments are not classified as fitting directly on test
data. Every finding must be reviewed with its source cell.

The v0.13 AST layer propagates train/test tags through assignments, containers,
and simple same-notebook function wrappers to identify renamed test data flowing
to `fit`/`fit_transform`. Dynamic dispatch, imports, closures, arbitrary helper
modules, and runtime-dependent aliases remain outside its guarantee.

## Frozen corpus

The real-artifact corpus contains all files matching three declared path
patterns at immutable upstream commits:

- 35 MONAI Model Zoo `models/*/configs/metadata.json` files;
- 18 Transformers `examples/pytorch/**/README.md` files;
- 7 TensorFlow Docs `site/en/tutorials/keras/*.ipynb` files.

Selection is exhaustive inside those patterns and was not filtered by whether
ReproCheck succeeded. The source manifest records the upstream URL, commit,
license, byte size, and SHA-256 of every artifact. The study result also embeds
the SHA-256 of the manifest and annotations plus all three commit IDs.

There are 40 annotated supported claims in 24 claim-bearing files. Thirty
labels are independently derived by a small annotation rule from explicit
MONAI `eval_metrics` fields. Ten narrative/Transformers labels were reviewed by
one internal reviewer. Seven notebook risk-label sets also have one internal
reviewer. There are zero external annotators and no adjudication. Rule-derived
labels reduce transcription error but are not independent expert judgement.

## Cross-repository challenge design

After the 0.5.0 source and wheel were frozen, but before its output was observed,
a second corpus was selected from two official repositories at immutable
commits: Detectron2 `MODEL_ZOO.md` and all 113 MMDetection
`configs/*/README.md` files. This yields 114 complete artifacts. Selection is
exhaustive inside the declared path patterns and is independent of evaluator
success.

An annotation program separate from the ReproCheck parser labels numeric cells
under AP, AP50, AP75, AR, and PQ table headers. It produced 1,006 labels in 89
claim-bearing artifacts. The labels are rule-derived internal annotations with
zero external reviewers and no adjudication. Narrative metrics, other metric
families, and ambiguous cells containing more than one number are outside the
declared scope.

The original 0.5 wheel, its SHA-256, the selected files, source commits, source
SHA-256 values, annotation SHA-256, and original result were frozen. A v2 replay
uses a table-only prediction scope and reproduces the original summary exactly.
Version 0.6 was then developed after examining the zero-shot errors. Therefore
the 0.5 result is zero-shot evidence, while the 0.6 result is explicitly a
development-set measurement and must not be presented as held-out accuracy.

## Measures and baseline

Claim matching requires the same canonical metric identifier and numerical
value within `1e-9`. The study reports TP, FP, FN, precision, recall, per-file
exactness, and Wilson 95% intervals. Empty-claim files remain in artifact-level
exactness but do not enter paired claim-recall resampling.

The naive comparison baseline is a published regex that recognizes only nearby
inline names for accuracy, precision, recall, F1, Dice, IoU, RMSE, MAE, and R2.
It intentionally does not parse Markdown tables or nested JSON. It is a weak,
transparent sanity baseline, not the strongest available system.

The stronger format-aware baseline is implemented independently from
ReproCheck's claim parser. It recursively reads the declared MONAI
`eval_metrics` object, parses ordinary Markdown pipe tables, supports simple
inline key/value output, and accepts equivalent numeric JSON strings. This
baseline has privileged knowledge of the corpus formats and is not a general
DOCX/PDF/notebook audit system. It is included specifically to prevent a weak
regex comparison from overstating parser novelty.

For every claim-bearing artifact, paired recall is ReproCheck recall minus
baseline recall. The reported mean uses a deterministic paired bootstrap with
5,000 samples and seed 2026. Wilson intervals quantify sample uncertainty for
aggregate precision and recall.

The mutation study uses 21 claim-bearing MONAI files. Each receives a large
value shift, a shift just outside tolerance, an unsupported metric insertion,
a shift inside tolerance, an equivalent percentage representation, and an
equivalent numeric-string representation. Four files with at least two
different metrics also receive a value-swap mutation. This produces 67 defects
that must be detected and 63 negative controls that must remain extracted and
supported. It tests structured numerical consistency, not arbitrary semantic
or methodological corruption.

Latency is recorded in the raw result but excluded from the frozen baseline
because it depends on hardware and system load.

## Frozen v0.5 results

| Measure | ReproCheck | Format-aware baseline | Naive inline baseline |
| --- | ---: | ---: | ---: |
| Annotated claim TP / FP / FN | 40 / 0 / 0 | 40 / 0 / 0 | 8 / 0 / 32 |
| Precision | 100.0% | 100.0% | 100.0% |
| Precision Wilson 95% | 91.24%-100% | 91.24%-100% | 67.56%-100% |
| Recall | 100.0% | 100.0% | 20.0% |
| Recall Wilson 95% | 91.24%-100% | 91.24%-100% | 10.50%-34.76% |
| Artifact exact rate, all 60 files | 100.0% | 100.0% | 68.33% |
| Defective mutations detected | 67/67 | 67/67 | 8/67 |
| Equivalent controls preserved | 63/63 | 63/63 | 12/63 |

The paired mean per-artifact recall difference is +72.92 percentage points;
the paired-bootstrap 95% interval is +56.25 to +87.50 points. ReproCheck also
matched 7/7 stored internal notebook risk-label sets. Against the format-aware
baseline, the paired recall difference is exactly 0 on this corpus. Therefore
the study does not establish claim-extraction superiority over a schema-aware
approach.

These are observed results on the frozen corpus only. The 100% values must not
be presented as universal accuracy, and the intervals do not remove annotation
bias. The deterministic source of truth is
`benchmarks/real_artifacts/baseline-v6.json`; `make study` reproduces and checks
it.

## Preregistered v0.6 holdout

After v0.6 and its wheel were frozen, a new holdout protocol fixed four official
repositories, path patterns, the AP/AP50/AP75 table-cell scope, matching rule,
and evaluator SHA-256 before source contents or evaluator output were observed.
The resolved commits, 25 complete artifacts, source hashes, 313 annotations,
annotation lock, and one-shot runner were then frozen before execution. The
annotation implementation is independent from ReproCheck and received one
internal pre-output review; it had no external reviewer or adjudicator.

| Measure | Frozen v0.6 zero-shot |
| --- | ---: |
| Labelled TP / FP / FN | 297 / 67 / 16 |
| Precision | 81.59% |
| Precision Wilson 95% | 77.29%-85.24% |
| Recall | 94.89% |
| Recall Wilson 95% | 91.86%-96.83% |
| Exact artifacts, all 25 | 92.00% |
| Exact claim-bearing artifacts, 15 | 86.67% |

All strict errors were confined to two Ultralytics files. Post-hoc inspection
found a frozen annotation error in `yolo-world.md`: 16 values under AP50/AP75
were categorized as AP, producing 16 FP and 16 FN despite matching values. In
`yolov7.md`, all 51 FP are genuine extraction of AP-small/medium/large columns
excluded by the preregistered scope. The preserved primary result is not
modified. Correcting only the annotation category error produces a diagnostic,
not primary, result of 313 TP, 51 FP, and 0 FN.

`make holdout` verifies the complete hash chain, schemas, exact expected result,
and post-hoc accounting. `make holdout-replay` installs the frozen v0.6 wheel in
a clean environment and requires byte-identical reproduction. Any parser fix
informed by this output must use a later version and a new unseen holdout.

Version 0.7 follows this versioning rule. It excludes AP-small/medium/large
columns and removes the 51 confirmed evaluator false positives on the inspected
holdout. The remaining strict 16 FP and 16 FN are the frozen annotation-category
error described above; using corrected post-hoc categories gives 313/313
matches. Both v0.7 measurements are development results after inspection and do
not alter the v0.6 primary result or establish v0.7 generalization.

## Cross-domain v0.7 holdout

A subsequent protocol froze the v0.7 wheel, exact commits for timm,
MMSegmentation, fairseq, and PaddleClas, hash-ranked path sampling, an 18-metric
scope, and matching rules before source content download. The realized corpus
contains 39 files and 295 labels; sources, independent annotation code, labels,
runner, and evaluation lock were all hashed before the one-shot evaluator run.

| Measure | Frozen v0.7 zero-shot |
| --- | ---: |
| Labelled TP / FP / FN | 259 / 0 / 36 |
| Precision | 100.00% |
| Precision Wilson 95% | 98.54%-100% |
| Recall | 87.80% |
| Recall Wilson 95% | 83.57%-91.05% |
| Exact artifacts, all 39 | 92.31% |
| Exact claim-bearing artifacts, 16 | 81.25% |

The evaluator recovered 249/249 mIoU, 4/4 Accuracy, and 6/42 Top-1/Top-5
claims. Post-hoc review found no annotation correction: all 36 misses are caused
by standalone Top-1/Top-5 headers that v0.7 does not map without an `accuracy`
token. The strict result is preserved. `make holdout-v07` verifies the complete
hash chain and requires byte-identical replay from the frozen wheel.

Version 0.8 was developed only after this result was inspected. It recognizes
standalone Top-1/Top-5 headers while rejecting Top-K error-rate headers and
recovers 295/295 labels without extras on the known corpus. This is correction
evidence, not zero-shot evidence; the v0.7 primary metrics remain unchanged.

## Challenge results

| Measure | Frozen 0.5 wheel | Post-inspection 0.6 wheel |
| --- | ---: | ---: |
| Labelled TP / FP / FN | 18 / 0 / 988 | 1,006 / 2 / 0 |
| Strict precision | 100.00% | 99.80% |
| Precision Wilson 95% | 82.41%-100% | 99.28%-99.95% |
| Recall | 1.79% | 100.00% |
| Recall Wilson 95% | 1.13%-2.81% | 99.62%-100% |
| Claim-bearing artifact exact rate | 1.12% | 100.00% |

The two strict 0.6 false positives are valid `Average Precision` cells in the
DeepFashion table that the frozen abbreviation-based label rule omitted. This
classification was made by one internal reviewer after evaluator inspection;
it is recorded in a separate post-hoc file and does not modify primary metrics.
The strict score therefore remains 1,006 TP, 2 FP, and 0 FN.

The large improvement demonstrates correction of the observed AP/AR/PQ
Markdown/HTML format gap. It does not estimate performance on another unseen
repository. `make challenge` verifies frozen sources, labels, schemas, and
expected matrices; `make challenge-replay` installs each hashed wheel in a
temporary environment and requires byte-identical deterministic output.

## Controlled benchmark acceptance criteria

- Zero false negatives for exact row overlap under declared identity columns.
- Zero false negatives for exact shared group identifiers.
- Exact deterministic classification/regression recomputation from one
  predictions file.
- Explicit AP and matching conventions for detection evidence.
- No silent overwrite when two evidence sources disagree beyond tolerance.
- Identical JSON findings across repeated runs, excluding `created_at`.
- Explicit `no_evidence` rather than an inferred value when evidence is absent.
- Fail-closed rejection of malformed inputs and altered certificates.

The separate controlled suite injects one known defect at a time and currently
contains 12 behavioral cases plus 3 malformed-input rejection cases.

## Preregistered PAWS lexical holdout

Version 0.12 separates threshold development on all 8000 PAWS-Wiki validation
pairs from a one-shot evaluation on 8000 test pairs. Before test content was
downloaded, commit `2f2ec247ce55fd1efadee27d42c3814186c289d9` fixed the exact
dataset and mirror revisions, file hashes, evaluator hash, nine methods,
thresholds, primary hypothesis, balanced-accuracy metric, and exact paired
McNemar test. The evaluator refuses to overwrite the locked result.

| Method | Validation balanced accuracy | Locked test balanced accuracy |
| --- | ---: | ---: |
| Hybrid lexical v1 | 56.19% | 54.94% |
| Ordered tokens v1 | 72.95% | 70.53% |
| Character SequenceMatcher | 71.66% | 69.43% |
| Logistic lexical features | 73.35% OOF | 66.48% |

The preregistered primary difference is +15.58 percentage points for ordered
tokens versus hybrid lexical on test. Of 3101 discordant pairs, ordered alone
is correct on 2247 and hybrid alone on 854; exact two-sided McNemar
`p = 7.07e-143`. Ordered-token precision is 66.20% and recall is 68.92%.

PAWS labels are independent of this project, but the project author selected
the corpus, task, methods, and analysis. Semantic paraphrase discrimination is
stricter and different from operational train-test contamination screening.
The result validates sensitivity to adversarial English word order, not a
universal leakage-detector accuracy claim.

## Threats to validity

- The corpus has only three repositories and 40 annotated claims.
- The challenge adds two repositories and 1,006 labels, but the 0.6 evaluator
  was adapted after those files were inspected; only the 0.5 result is zero-shot.
- Challenge labels are generated by one internal rule. The two identified label
  omissions have one post-hoc internal reviewer, not independent adjudication.
- The preregistered v0.6 holdout has only four repositories, three associated
  with Ultralytics, covers AP-family computer-vision tables, and has one internal
  annotation reviewer without blinded adjudication.
- Most annotations are rule-derived; the rest have one internal reviewer.
- The regex comparator is deliberately weak. The format-aware comparator ties
  ReproCheck but has privileged corpus-format knowledge; neither result proves
  state-of-the-art extraction on unseen repositories.
- A parser can miss uncommon phrasing outside the declared corpus.
- A correct metric can originate from an invalid experimental design.
- Hybrid lexical matching catches controlled typos and word-boundary changes.
  Ordered matching improves substantially on the locked English PAWS test but
  remains a lexical heuristic and does not establish multilingual semantic or
  visual-duplicate detection.
- Uploaded evidence can be fabricated. Hashes preserve what was audited but do
  not prove how the files were produced.
- The certificate checksum alone is not a digital signature. An optional
  detached Ed25519 signature establishes possession of a key, but author
  identity still depends on independent authentication of that public key and
  no trusted timestamp is provided.
- A `supported` claim has not been independently recomputed.
- Static notebook findings are risk indicators, not proven defects.
- Detection mAP uses ReproCheck's declared matching/interpolation conventions;
  it does not implement COCO `iscrowd`, ignore regions, area ranges, or maxDets
  and is not claimed to be byte-equivalent to official COCOeval.

The strongest next scientific step is dual independent annotation of a new,
broader preregistered holdout, followed by blinded adjudication and comparison
with stronger document-extraction baselines. The current holdout establishes
real zero-shot evidence but does not satisfy that external-review standard.
