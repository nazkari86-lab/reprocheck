# ReproCheck-ML ISEF Research Design

Date: 2026-08-21  
Status: implementation complete through preregistration scaffold; authentic corpus and external evaluation pending  
Target category: Regeneron ISEF Software Design — Algorithms  
Research year: 2026–2027 continuation of ReproCheck

## 1. Plain-language project definition

ReproCheck-ML reads a machine-learning project, finds numerical result claims such as
“the model achieved 94% accuracy,” locates the files that could support the claim,
recomputes the metric, and shows one of three outcomes:

- **confirmed** — the supplied evidence reproduces the reported value;
- **not confirmed** — the recomputed value differs from the reported value;
- **insufficient evidence** — the project does not contain enough compatible evidence.

Machine learning finds what may need checking and where evidence may be located. A
deterministic verifier performs the final computation. The system evaluates whether a
claim is supported by supplied artifacts; it does not judge the honesty of an author.

## 2. Research contribution for the current year

Existing ReproCheck releases are prior work and form the deterministic baseline. The
2026–2027 contribution is a new **Evidence-Constrained Selective Verification** method
that learns to discover claims and candidate evidence while limiting false alerts.

The current-year work consists of:

1. a public, provenance-bound corpus of claim-bearing and non-claim text blocks from
   independent machine-learning repositories;
2. a learned claim detector and structured claim extractor;
3. a learned claim-to-evidence ranker;
4. a deterministic evidence-compatibility layer;
5. a calibrated three-way decision policy: `verify`, `review`, or `abstain`;
6. an owner-disjoint benchmark and a later prospective external holdout;
7. ablation, robustness, calibration, language, and efficiency studies;
8. an evidence-first interface that exposes every source and computation.

Historical ReproCheck benchmarks, implementations, results, and interface components
must be labeled as prior work in the notebook, continuation form, repository, poster,
and interview. Only new data collection and experiments within the eligible research
window may be presented as current-year experimental work.

## 3. Research question and hypotheses

### Primary research question

Can a learned evidence-constrained selective system recover more verifiable numerical
claims from previously unseen machine-learning projects than deterministic rules while
maintaining high precision and exposing a reproducible evidence path for every verdict?

### Primary hypothesis

On an owner-disjoint hidden test set, the full method will improve end-to-end claim
recall by at least 15 percentage points over frozen ReproCheck 0.30.4 while achieving:

- point precision of at least 95%;
- Wilson 95% lower bound for precision of at least 90%;
- automatic decision coverage of at least 70% of eligible claims.

### Secondary hypotheses

1. Evidence constraints will reduce false claim-to-artifact links relative to a text-only
   transformer.
2. Selective abstention will improve precision at a measurable coverage cost relative to
   a fixed argmax classifier.
3. The full model will outperform both a TF-IDF logistic baseline and a transformer
   without evidence constraints.
4. Performance will decline under domain and language shift, but the selective policy
   will retain the preregistered precision target by abstaining more often.
5. No single component will explain the full gain; removing claim context, evidence
   constraints, or calibration will measurably worsen an associated metric.

## 4. Scope

### Supported claim families

The primary experiment is limited to numerical result claims for:

- accuracy;
- precision;
- recall or sensitivity;
- specificity;
- F1;
- AUROC and AUPRC;
- log loss and Brier score;
- Dice and IoU;
- mAP and mAR.

### Supported evidence

- Markdown, HTML, PDF, DOCX, notebook Markdown, JSON, and CSV report text;
- label and prediction tables from which supported metrics can be recomputed;
- structured metric exports;
- detection evidence supported by the existing deterministic AP evaluator;
- project manifests that bind reports, evidence, model, dataset, split, run, and variant.

### Explicit exclusions

- truth of broad causal or biomedical conclusions;
- verification against the global scientific literature;
- execution of uploaded notebooks or arbitrary project code;
- automatic accusation of fraud or misconduct;
- unsupported generative explanations;
- images of charts as primary evidence in the first preregistered experiment;
- claims outside the declared metric ontology in the primary score.

Out-of-scope inputs may be displayed as exploratory results but cannot alter the primary
benchmark score.

## 5. System architecture

```text
project files
    │
    ├── deterministic document parser ──> immutable text blocks
    │                                        │
    │                                        ▼
    │                              learned claim detector
    │                                        │
    │                                        ▼
    │                         structured claim tuple extractor
    │                                        │
    ├── deterministic artifact inventory ────┼──> learned evidence ranker
    │                                        │
    │                                        ▼
    │                           evidence compatibility checks
    │                                        │
    │                                        ▼
    │                         calibrated selective decision gate
    │                              │         │          │
    │                           verify     review     abstain
    │                              │
    ▼                              ▼
deterministic metric recomputation and evidence graph
    │
    ▼
confirmed / not confirmed / insufficient evidence
```

The learned layer never writes a final `confirmed` or `not_confirmed` result directly.
Only the deterministic verifier may emit these verdicts after validating an evidence
contract and recomputing or directly comparing a supported metric.

## 6. Data model

### Repository record

Each repository record contains:

- stable repository and owner identifiers;
- immutable commit SHA;
- source URL and retrieval timestamp;
- detected license;
- SHA-256 and byte length for every selected file;
- task/domain label;
- primary language label;
- selection reason recorded before annotation;
- train, validation, test, or prospective-holdout assignment.

Repository identifiers remain private from the model only when required for blinded
evaluation. Provenance remains available to curators and later public release.

### Text block record

Each block contains:

- repository and document identifiers;
- byte-stable source locator;
- raw and normalized text;
- block type: prose, table row, JSON path, notebook cell, or other;
- language;
- binary `contains_eligible_claim` label;
- zero or more claim annotations;
- annotation status and disagreement record.

### Claim tuple

```text
(metric, value, unit, model, dataset, split, task, experiment, run, variant)
```

`metric` and `value` are mandatory for an eligible primary claim. Other fields may be
missing but must never be invented. Every populated field includes an exact source span
or structured source path.

### Evidence candidate

Each candidate contains:

- artifact ID and role;
- structured selector, when applicable;
- compatible context fields;
- evidence grade: raw/recomputed, structured reported, or text-only reported;
- candidate generation method;
- deterministic compatibility failures;
- final review label.

## 7. Corpus construction

### Target size

- at least 100 independent development repositories and owners acquired before model
  freeze;
- at least 30 additional independent repositories and owners acquired only after model
  freeze for the prospective holdout;
- at least 5,000 annotated blocks;
- at least 1,000 eligible claims;
- at least 300 complete claim-to-evidence pairs;
- at least 20 development repositories in each of the computer-vision, NLP, and other-ML
  domain groups, with at least five owners from each group in the hidden test;
- a secondary target of at least 100 authentic blocks and 20 eligible claims in each of
  Russian and Kazakh. A language below this target is reported descriptively and is not
  used for a confirmatory language-comparison claim.

### Selection

Repositories are selected using a frozen search protocol before annotations are viewed.
Selection must not depend on whether current ReproCheck succeeds. One repository per
owner is permitted in the primary corpus. Forks, mirrors, prior ReproCheck development
repositories, user-owned repositories, and projects inspected while designing parser
rules are excluded from hidden and prospective evaluation.

### Annotation

The annotation guide defines eligibility, span boundaries, tuple fields, evidence
compatibility, and hard negatives. A primary annotator labels each block. A second
annotator independently reviews every positive claim, every evidence pair, every model
error candidate used in the final score, and a random sample of negatives. Disagreements
are adjudicated before opening model results.

Annotator agreement is reported using raw agreement and a chance-corrected statistic
appropriate to the label structure. Agreement is evidence about annotation reliability,
not model accuracy.

Human annotators who create research data are treated according to the determination of
the local SRC/IRB. No survey, usability test, timing study, or analysis of annotator
behavior may begin until the required preapproval is documented.

### Leakage prevention

- group splits use owner as the indivisible unit;
- near-duplicate text is detected across splits before training;
- repository names, owner names, URLs, and commit identifiers are removed from model
  input;
- translated or templated variants remain in the same split as their source;
- weak labels from ReproCheck rules may initialize training data but cannot serve as
  ground truth in validation, test, or prospective holdout;
- all split manifests are frozen and hashed before model selection.

## 8. Learned components

### 8.1 Claim detector

Input: one text block with bounded neighboring context.  
Output: probability that the block contains at least one eligible result claim.

Required baselines:

1. frozen ReproCheck 0.30.4 rules;
2. character/word TF-IDF with logistic regression;
3. compact multilingual transformer classifier.

The production candidate set is the union of deterministic-rule candidates and learned
candidates so ML can improve recall without deleting known-good deterministic coverage.

### 8.2 Structured tuple extractor

Numbers are enumerated deterministically. The model scores metric aliases and context
spans around each number rather than generating arbitrary JSON. A constrained decoder
constructs only schema-valid tuples. Values are parsed from the original source span,
never generated as free text.

### 8.3 Evidence ranker

The ranker scores a claim against bounded artifact summaries and structured selectors.
Candidate generation remains complete for declared structured evidence types. The model
only changes ranking and review cost; it cannot silently remove a deterministically
compatible candidate from evaluation.

Training uses positive claim-evidence pairs plus hard negatives from:

- a different split of the same experiment;
- a different model or dataset;
- a different run or variant;
- the same metric with a different value;
- a plausible artifact from another project.

### 8.4 Evidence compatibility layer

Deterministic constraints reject a candidate when populated context fields conflict.
They check metric family, unit, model, dataset, split, task, experiment, run, variant,
artifact integrity, and required columns. Missing context lowers evidence completeness;
conflicting context blocks automatic verification.

### 8.5 Selective decision gate

The gate combines declared, inspectable signals:

- calibrated claim probability;
- tuple completeness;
- evidence ranker score and rank margin;
- deterministic compatibility result;
- evidence grade;
- out-of-distribution indicators;
- agreement between learned and rule-based extraction.

Thresholds are chosen only on the calibration split to maximize automatic coverage
subject to a preregistered precision constraint. The test and prospective holdout reuse
the frozen thresholds unchanged.

The gate returns:

- `verify` when the complete contract passes and calibrated risk is acceptable;
- `review` when a bounded human decision could resolve ambiguity;
- `abstain` when evidence is absent, conflicting, unsupported, or out of distribution.

## 9. Evaluation protocol

### Frozen splits

- development train: 60% of owners;
- development calibration/validation: 20% of owners;
- hidden test: 20% of owners;
- prospective holdout: at least 30 newly acquired owners and at least 100 eligible claims
  after code, weights, ontology, thresholds, and evaluation scripts are frozen.

Exact counts may vary because owner groups are indivisible. The split generator records
its seed, version, group balance, and hashes.

### Primary unit

The primary unit is an eligible source claim. A prediction is correct only when metric,
normalized value, and required evidence link match the adjudicated annotation. Duplicate
predictions cannot earn duplicate credit.

### Primary metrics

- end-to-end claim recall;
- end-to-end precision;
- Wilson 95% confidence intervals;
- automatic coverage;
- risk-coverage curve and area under that curve;
- complete-document recovery rate;
- exact claim-to-evidence rate.

### Secondary metrics

- block classification precision, recall, F1, and PR-AUC;
- tuple exact match and field-level F1;
- evidence recall@1, recall@3, MRR, and exact compatible-evidence rate;
- expected calibration error and Brier score;
- latency, peak memory, and model size;
- per-language and per-domain outcomes with denominators and intervals.

### Statistical comparisons

- paired bootstrap confidence intervals over owner groups for recall differences;
- McNemar-style paired analysis where its assumptions match the binary paired outcome;
- Wilson intervals for proportions;
- multiplicity-aware interpretation of secondary comparisons;
- effect sizes and confidence intervals reported alongside p-values.

No isolated p-value is treated as proof of practical superiority.

### Success gate

The primary result passes only if all are true on the prospective holdout:

1. the development corpus contains at least 100 independent eligible owners, and the
   prospective cohort contains at least 30 additional owners and 100 eligible claims;
2. end-to-end recall improves by at least 15 percentage points over frozen rules;
3. precision is at least 95%;
4. the Wilson 95% lower precision bound is at least 90%;
5. automatic coverage is at least 70%;
6. provenance, predictions, exclusions, and failures are complete and independently
   replayable.

Failure of any condition is published as a negative or inconclusive result. Thresholds
may not be changed and the same cohort may not be relabeled as a new zero-shot test.

## 10. Required experiments

### Baseline comparison

- rules only;
- TF-IDF logistic regression;
- transformer claim detector;
- transformer plus tuple extractor;
- transformer plus evidence ranker;
- full evidence-constrained selective method;
- optional frozen zero-shot LLM baseline with exact model/version/prompt recorded.

The LLM baseline is not a dependency of the final verifier and cannot receive private
holdout labels or artifacts through an external service without explicit protocol and
privacy approval.

### Ablations

- remove rule/ML union;
- remove structured context;
- remove evidence constraints;
- remove rank margin;
- remove calibration;
- replace selective gate with argmax;
- remove out-of-distribution signal;
- train without hard negatives.

Each ablation has one declared expected effect and one primary associated metric.

### Robustness

- numeric substitution;
- metric-name substitution;
- percent/unit conversion;
- model, dataset, and split swaps;
- table-to-prose and prose-to-table transformations;
- Unicode punctuation and decimal separators;
- malformed and oversized documents;
- irrelevant numbers near metric terms;
- contradictory evidence files.

Controlled mutations measure capability and do not replace natural external evidence.

### Shift analysis

- computer vision versus NLP versus other ML domains;
- familiar versus unseen document formats;
- English versus Russian versus Kazakh where authentic sample sizes permit;
- recent repositories versus older repositories;
- in-distribution versus preregistered out-of-distribution strata.

## 11. Error taxonomy

Every false positive, false negative, wrong evidence link, and inappropriate automatic
decision receives exactly one primary cause and optional contributing causes:

- eligibility ambiguity;
- missed claim block;
- wrong metric span;
- wrong value or unit;
- missing context;
- context conflict missed;
- evidence candidate absent;
- evidence ranking error;
- unsupported deterministic metric;
- calibration/selective-gate error;
- corrupted or incomplete artifact;
- annotation error;
- distribution shift;
- implementation defect.

Corrections discovered after unblinding remain documented, but the frozen score remains
immutable.

## 12. Product and demonstration design

The existing visual evidence graph remains. ReproCheck-ML adds a simple judge-facing
workflow without replacing the approved graph interface.

### Main screen

1. Upload or select a frozen demonstration project.
2. Show the exact claim highlighted in its source document.
3. Show the matched evidence file and relevant rows.
4. Show reported and recomputed values side by side.
5. Show `confirmed`, `not confirmed`, or `insufficient evidence` in plain language.
6. Show why the ML layer chose `verify`, `review`, or `abstain`.
7. Open the evidence graph and deterministic formula on demand.

### Evidence passport

Every result displays:

- scope and unsupported claim families;
- source paths and SHA-256 digests;
- model and threshold versions;
- evidence completeness;
- reported and recomputed values;
- formula and parameters;
- decision path;
- limitations and review status;
- a reproducible command and downloadable certificate.

### Demonstration cases

- one correctly reported result;
- one natural mismatch;
- one insufficient-evidence case;
- one nonstandard phrase found by ML but missed by rules;
- one high-confidence-looking case where the system correctly abstains.

The demonstration must work offline because ISEF displays cannot rely on internet access.

## 13. Safety, ethics, and competition compliance

### Communication

- use “not confirmed by supplied evidence,” not “false” or “fraudulent”;
- never infer intent or misconduct;
- expose model limitations and abstentions;
- do not upload private project artifacts to third-party model APIs by default;
- preserve copyright, repository licenses, and source attribution.

### Human participants

Technical benchmarking on public repositories is the primary study. Any survey,
usability test, annotation-behavior analysis, or teacher/student product test requires a
written local SRC/IRB determination and all required approval before recruitment or data
collection. A later approval cannot repair earlier human-participant experimentation.

### AI assistance

All AI assistance in code, analysis, literature discovery, or research tooling is logged
with date, tool, purpose, output used, and the student's verification. The student must
understand and independently defend every algorithm and result. Research-plan, abstract,
poster, interview answers, and citations must comply with the applicable ISEF rules and
be written and verified by the student in their own words.

### Continuation

Form 7 and repository documentation must separate prior ReproCheck work from the new
ML method, new corpus, and new experiments. Historical data cannot be presented as
current-year data. The eligible 12-month research window and local affiliated-fair rules
control what may appear in the final ISEF submission.

## 14. Reproducibility and release

The study release contains:

- preregistration and cryptographic lock;
- source-selection protocol;
- source manifest and permitted redistributable corpus content;
- annotation guide, review packets, adjudication log, and agreement results;
- split manifests and leakage report;
- source code, lockfile, model configuration, seeds, and environment metadata;
- trained weights when licensing permits;
- frozen predictions for every baseline and ablation;
- evaluation scripts and machine-readable results;
- model card, dataset card, evidence graph, certificates, and checksums;
- negative, excluded, failed, and abstained cases;
- offline demonstration package.

Training and evaluation commands must reproduce all tables and figures from immutable
inputs. CI verifies schemas, hashes, deterministic evaluation, historical score locks,
tests, lint, types, package build, and a clean-environment smoke test.

## 15. Claim boundaries

### Permitted after implementation but before external success

- “We implemented an evidence-constrained selective verification method.”
- “The system was evaluated on a frozen owner-disjoint development benchmark.”
- exact development results with explicit labels and limitations.

### Permitted only after the prospective gate passes

- “The method improved recall by the measured amount on the preregistered prospective
  cohort while meeting its precision and coverage targets.”

### Never permitted from this study alone

- “ReproCheck detects all false scientific claims.”
- “The model proves whether a researcher is honest.”
- “The system is universally 95% accurate.”
- “The method is the first scientific claim verifier.”
- “The project is guaranteed to win ISEF.”

## 16. ISEF-ready outcome definition

The design has top-level ISEF potential only if the completed current-year work shows:

1. a clearly student-understood and student-defended original method;
2. authentic public inputs and auditable annotations;
3. a frozen, owner-disjoint, prospective evaluation;
4. a meaningful gain over strong baselines under a false-alert constraint;
5. complete failure analysis and honest negative results;
6. a working offline prototype with inspectable evidence;
7. clear separation of prior work, mentor/AI assistance, and current-year contribution;
8. compliance with all SRC, IRB, copyright, privacy, and AI-use requirements.

A successful implementation can have 10/10 **design potential**. A score or award cannot
be guaranteed, and the project must remain explicitly unvalidated until the prospective
result exists.

## 17. Primary references

- Society for Science. Grand Award Judging Criteria.
  https://www.societyforscience.org/isef/grand-award/criteria/
- Society for Science. 2027 International Rules and Guidelines.
  https://www.societyforscience.org/isef/international-rules/
- Society for Science. Human Participants.
  https://www.societyforscience.org/isef/international-rules/human-participants/
- Society for Science. Software Design category.
  https://www.societyforscience.org/isef/categories-and-subcategories/software-design/
- Wadden et al. Fact or Fiction: Verifying Scientific Claims. EMNLP 2020.
  https://aclanthology.org/2020.emnlp-main.609/
- Wadden et al. SciFact-Open. Findings of EMNLP 2022.
  https://aclanthology.org/2022.findings-emnlp.347/
- Lu et al. SCITAB. EMNLP 2023.
  https://aclanthology.org/2023.emnlp-main.483/
- Gangrade et al. Selective Classification via One-Sided Prediction. AISTATS 2021.
  https://proceedings.mlr.press/v130/gangrade21a.html
- Li et al. Minimal Evidence Group Identification for Claim Verification. TrustNLP 2025.
  https://aclanthology.org/2025.trustnlp-main.8/
