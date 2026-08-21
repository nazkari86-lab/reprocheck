# ReproCheck-ML ISEF Implementation Plan

**Goal:** Implement the approved Evidence-Constrained Selective Verification research
system without weakening ReproCheck's deterministic audit, evidence graph, or frozen
historical results.

**Design:** `docs/superpowers/specs/2026-08-21-reprocheck-ml-isef-design.md`

**Architecture:** Learned components emit bounded candidates and scores. Typed,
deterministic compatibility checks and a calibrated selective gate decide whether a
candidate can proceed to the existing verifier. Only the existing deterministic audit
may emit a final evidence verdict.

**Technology:** Python 3.11+, scikit-learn baseline, optional PyTorch/Transformers model,
JSON Schema, NumPy-compatible serialized arrays, existing FastAPI UI, pytest, Ruff,
Pyright, uv, Hatch, and Make.

## Delivery constraints

- Preserve all immutable historical benchmark scores and registrations.
- Preserve the existing evidence graph and website composition.
- Keep the default deterministic install usable without ML dependencies.
- Never execute uploaded repository code or notebooks.
- Never let an ML output directly become `confirmed` or `not_confirmed`.
- Keep repository/owner groups isolated across data splits.
- Freeze model, ontology, calibration, code, and evaluator before prospective retrieval.
- Report negative results and abstentions without post-hoc threshold changes.

## Task 1 — Typed ML contracts and deterministic decision core

**Create:**

- `src/reprocheck/ml_contracts.py`
- `src/reprocheck/ml_decision.py`
- `tests/test_ml_contracts.py`
- `tests/test_ml_decision.py`

**Deliver:**

- immutable claim tuple, evidence candidate, model score, compatibility result, and
  selective decision dataclasses;
- strict finite/range validation;
- deterministic context compatibility;
- evidence completeness calculation;
- fail-closed `verify`, `review`, `abstain` gate;
- canonical JSON serialization suitable for certificates;
- unit and adversarial tests.

**Gate:** focused tests, Ruff, and Pyright pass; no existing API changes.

## Task 2 — Corpus manifest and annotation contracts

**Create:**

- `src/reprocheck/ml_dataset.py`
- `src/reprocheck/schemas/ml-corpus-v1.schema.json`
- `src/reprocheck/schemas/ml-annotations-v1.schema.json`
- `tests/test_ml_dataset.py`
- `benchmarks/reprocheck_ml_v1/annotation-guide.md`

**Deliver:**

- provenance-bound repository, block, claim, span, and evidence-pair records;
- exact source SHA-256 and byte length verification;
- schema validation with unknown-field rejection;
- duplicate/fork/owner exclusion gates;
- annotation disagreement and adjudication records;
- safe local paths and immutable corpus descriptors.

**Gate:** corrupted sources, traversal, duplicate owners, malformed spans, non-finite
values, and unresolved annotations fail closed.

## Task 3 — Owner-disjoint splitting and leakage audit

**Create:**

- `src/reprocheck/ml_split.py`
- `tests/test_ml_split.py`

**Deliver:**

- deterministic 60/20/20 owner-group split;
- domain-aware balancing with explicit infeasibility output;
- prospective-owner isolation;
- cross-split normalized and near-duplicate report;
- translation/template lineage grouping;
- frozen split manifest and digest.

**Gate:** property tests prove no owner or lineage crosses a split and repeat runs are
byte-identical for the same seed.

## Task 4 — Deterministic and classical ML baselines

**Create:**

- `src/reprocheck/ml_features.py`
- `src/reprocheck/ml_baselines.py`
- `tests/test_ml_baselines.py`

**Modify:**

- `pyproject.toml`
- `uv.lock`

**Deliver:**

- frozen ReproCheck 0.30.4 candidate baseline;
- word/character TF-IDF logistic classifier;
- deterministic numeric-candidate and context features;
- model artifact with feature vocabulary, labels, versions, seed, and training digest;
- no network requirement for inference.

**Gate:** clean-environment training and inference reproduce frozen predictions.

## Task 5 — Structured tuple extraction

**Create:**

- `src/reprocheck/ml_extraction.py`
- `tests/test_ml_extraction.py`

**Deliver:**

- deterministic enumeration of source numbers;
- bounded metric/context span candidate generation;
- constrained schema-valid tuple decoder;
- exact source spans for every populated field;
- no generated numeric values;
- tuple exact-match and field-F1 evaluator.

**Gate:** every emitted value maps byte-for-byte to a source span or structured path.

## Task 6 — Evidence retrieval and ranking

**Create:**

- `src/reprocheck/ml_retrieval.py`
- `tests/test_ml_retrieval.py`

**Deliver:**

- complete deterministic candidate generation for supported artifacts;
- classical learned ranker with hard-negative support;
- top-k ranking, margin, compatibility features, and reproducible artifact;
- recall@1, recall@3, MRR, and exact compatible-evidence evaluation.

**Gate:** ranker may reorder but cannot delete deterministically compatible candidates.

## Task 7 — Calibration and selective-risk evaluation

**Create:**

- `src/reprocheck/ml_calibration.py`
- `src/reprocheck/ml_evaluation.py`
- `tests/test_ml_calibration.py`
- `tests/test_ml_evaluation.py`

**Deliver:**

- calibration-only threshold selection;
- maximum-coverage search under precision constraints;
- Wilson intervals, owner-cluster bootstrap, risk-coverage curve, PR-AUC, ECE, and Brier;
- immutable per-example predictions;
- preregistered success-gate evaluator;
- explicit insufficient-sample outcome.

**Gate:** thresholds cannot be fit or changed from test labels; synthetic edge cases and
independent reference calculations match.

## Task 8 — Optional multilingual transformer

**Create:**

- `src/reprocheck/ml_transformer.py`
- `tests/test_ml_transformer.py`
- `benchmarks/reprocheck_ml_v1/model-card.md`

**Modify:**

- `pyproject.toml`
- `uv.lock`

**Deliver:**

- optional, pinned multilingual encoder training/inference path;
- deterministic seeds and environment capture;
- local/offline inference from a frozen model directory;
- English, Russian, and Kazakh subgroup metrics;
- out-of-distribution and confidence outputs.

**Gate:** core package and deterministic mode remain importable without transformer
dependencies; a small fixture model exercises the interface in CI.

## Task 9 — CLI, web, and evidence-passport integration

**Modify:**

- `src/reprocheck/cli.py`
- `src/reprocheck/web.py`
- `src/reprocheck/templates/index.html`
- `src/reprocheck/static/app.js`
- `src/reprocheck/static/styles.css`
- `src/reprocheck/evidence_graph.py`

**Test:**

- `tests/test_cli_extensions.py`
- `tests/test_web.py`
- `tests/test_evidence_graph.py`
- new browser-facing contract tests

**Deliver:**

- `ml-corpus-validate`, `ml-split`, `ml-train`, `ml-calibrate`, and `ml-evaluate` commands;
- optional ML discovery in the audit workflow;
- plain-language `verify`, `review`, and `abstain` presentation;
- reported versus recomputed values;
- model/version/threshold disclosure;
- preserved interactive evidence graph;
- offline judge demonstration cases.

**Gate:** deterministic UI remains unchanged when ML is disabled; desktop/mobile and
keyboard interactions pass browser verification.

## Task 10 — Frozen benchmark and prospective protocol

**Create under `benchmarks/reprocheck_ml_v1/`:**

- `protocol.md` and `protocol.json`
- `source-frame.json`
- `exclusions.json`
- `schema/`
- `acquire.py`
- `annotate.py`
- `split.py`
- `train.py`
- `calibrate.py`
- `evaluate.py`
- `register.py`
- `verify-registration.py`
- `README.md`

**Deliver:** executable hash-bound preregistration; development acquisition and
annotation tools; frozen hidden evaluation; separate post-freeze prospective acquisition;
independent review packets; immutable result and complete negative/error records.

**Gate:** registration verifier binds every executable input before prospective source
retrieval. A failed or undersized cohort remains a published unscored result.

## Task 11 — Scientific studies and figures

**Deliver:**

- baseline comparison;
- component ablations;
- controlled robustness mutations;
- domain and language shift;
- calibration and risk-coverage analysis;
- owner-cluster confidence intervals;
- latency, memory, and model-size measurements;
- complete error taxonomy;
- machine-generated tables and figures from frozen result JSON.

**Gate:** every number on the scorecard and every plotted point traces to a frozen
machine-readable result.

## Task 12 — Release, documentation, and completion audit

**Modify:** README, architecture, scientific protocol, scorecard, reproducibility,
authorship/AI disclosure, Makefile, schemas, package metadata, CI, and release notes.

**Verify:**

1. focused and full pytest suite;
2. coverage threshold;
3. Ruff and Pyright;
4. schema and benchmark registration verifiers;
5. package build and clean-venv smoke test;
6. supply-chain and dependency audit;
7. offline UI/browser verification;
8. deterministic replay of all reported tables and figures;
9. clean worktree and exact remote SHA after publication.

The project is not called externally validated or ISEF-ready until the prospective gate
has an eligible cohort, independent labels, frozen replay, and passing preregistered
thresholds. Engineering completion and scientific validation remain separate statuses.

