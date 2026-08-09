# Expanded experiment suite

## Why these experiments were added

The existing studies covered controlled audit defects, claim extraction on
public repositories, frozen zero-shot failures, lexical leakage, and indexed
search. Four gaps remained testable without pretending to have external human
reviewers:

1. What each integrity layer actually detects under different attacker effort.
2. Whether controlled corruptions of real source-derived artifacts are found.
3. Whether equivalent numerical representations preserve parser behavior.
4. Whether claim-to-graph construction remains structurally correct as the
   number of claims grows.

The protocol and runner files were committed in `f244e88` before the first
recorded run. `benchmarks/experiment-design-v1.lock.json` freezes their SHA-256
digests. This establishes chronology, not independence: all four designs remain
author-created controlled evidence.

## Integrity threat-model stress

Nine mutation families were applied at three threat levels.

| Threat level | Result | Correct interpretation |
| --- | ---: | --- |
| Payload changed without resealing | 9/9 detected | Outer certificate checksum detects payload changes relative to its stored digest |
| Outer certificate checksum recomputed, graph-local hashes stale | 9/9 detected | Node, edge, graph, and structural verification add defense beyond the outer checksum |
| Every unkeyed hash recomputed | 6/9 detected | Six structural violations remain invalid; three schema-valid semantic substitutions pass unsigned verification |
| Fully rehashed certificate checked against original Ed25519 signature | 9/9 detected | A trusted signature authenticates the exact frozen certificate bytes |

The three unsigned passes are `node_label`, `node_attribute`, and
`edge_relation`. This is not a bug hidden by the benchmark. SHA-256 is unkeyed:
an attacker who can rewrite the certificate can also recompute all embedded
hashes. The graph provides content addressing, internal consistency, and
structural validation; authenticity against such an attacker requires a
previously trusted digest or Ed25519 signature and authenticated public key.

This benchmark is a mechanism test. Repeating generated mutations does not
estimate attack prevalence, and no p-value is reported.

## Real-artifact corruption study

The runner first verifies frozen manifests and then copies deterministic Iris,
Diabetes, and YOLO26n/COCO8 artifacts into temporary directories. It applies
eight mutations without modifying the originals.

| Mutation family | Cases | Primary detection |
| --- | ---: | ---: |
| Reported claim changed | 3 | 3/3 |
| Raw predictions/detections changed | 3 | 3/3 |
| Supplied metric changed | 1 | 1/1 |
| Train/test overlap introduced | 1 | 1/1 |
| Clean negative controls | 3 | 3/3 correctly preserved |

Primary corruption sensitivity was 8/8 and control specificity was 3/3. Three
prediction/detection cases also produced downstream `claim_metric_mismatch`
findings beyond the preregistered primary `metric_evidence_conflict`; these are
reported as additional consequences, not extra independent successes.

The files originate from real deterministic benchmarks, but mutation choice and
labels are author-designed development evidence. This is stronger than a fully
synthetic smoke test and weaker than a natural sample of real research errors.

## Representation robustness

The 13-case matrix covers decimal and percentage scaling, decimal comma,
scientific notation, negative regression values, Russian prose, Markdown and
HTML tables, Top-1/Top-5 tables, detection metrics, and two negative controls.
All 12 in-scope cases matched the exact declared metric-value multiset.

A spelled-out English number is explicitly out of scope. It is included as a
negative capability declaration, not counted as evidence of semantic parsing.
The matrix is small and author-designed, so 100% is capability coverage only.

## End-to-end scalability

Each size was run five times through Markdown extraction, `run_audit`, evidence
graph construction, JSON certificate generation, and certificate verification.

| Claims | Graph nodes | Graph edges | Certificate bytes | Median wall time on recorded Mac |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 32 | 51 | 22,478 | 7.0 ms |
| 100 | 302 | 501 | 207,418 | 62.8 ms |
| 1,000 | 3,002 | 5,001 | 2,069,265 | 664.2 ms |

All 15 runs extracted the exact claim count, produced identical structural
counts, and passed certificate verification. Node, edge, and byte counts scale
approximately linearly in this synthetic workload. Wall times are descriptive
for the recorded environment and are deliberately excluded from the regression
baseline.

## Full evidence matrix

| Experiment family | Phase | What it supports | Status |
| --- | --- | --- | --- |
| Controlled defect benchmark | Controlled | Finding correctness and invalid-input rejection | Complete |
| Evidence-layer ablation | Controlled paired | Incremental observability from evidence levels | Complete |
| Integrity threat-model stress | Controlled mechanism | Exact checksum/graph/signature boundaries | Complete |
| Real-artifact corruptions | Source-derived controlled | Detection on three practical domains | Complete |
| Representation robustness | Controlled capability | Declared numeric format coverage | Complete |
| End-to-end scalability | Synthetic scaling | Structural correctness through 1,000 claims | Complete |
| Real-artifact study | Frozen development corpus | Claim extraction and baseline comparison | Complete |
| Cross-repository v0.5 challenge | Frozen zero-shot | Preserved 1.79% generalization failure | Complete |
| v0.6 preregistered holdout | Zero-shot | 81.59% precision, 94.89% recall | Complete |
| v0.7 cross-domain holdout | Zero-shot | 100% observed precision, 87.80% recall | Complete |
| Post-holdout v0.7/v0.8 | Development | Narrow correction behavior | Complete |
| Near-duplicate controlled set | Controlled | Lexical mutation coverage | Complete |
| PAWS locked test | Preregistered external labels | Ordered-token lexical behavior | Complete |
| Text-index benchmark | Synthetic scaling | Candidate/score reduction | Complete |
| Iris/Diabetes/YOLO external audits | Deterministic integrations | End-to-end task diversity | Complete |
| Dual external annotation | Independent human review | Annotation reliability and bias reduction | Ready, **not executed** |
| Reviewer workload study | Human practical validation | Time/error reduction | Not designed or executed |

The suite therefore expands coverage but does not remove the main external
validity limitation. Many completed experiments share the same author and code.
They must not be counted as independent replications merely because there are
many rows.

## Reproduction

```bash
make expanded-experiments
```

The complete repository gate includes this target. Frozen results and their
hashes are under each benchmark directory and
`benchmarks/expanded-results-v1.lock.json`.
