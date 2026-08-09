# Evidence-layer ablation

## Research question

Which inconsistency classes become observable when an auditor receives, in
order, report text, supplied metrics, primary artifacts, and a verified evidence
graph?

This is an information ablation, not a contest between four equally informed
parsers. Each level is deliberately restricted to the evidence named below.

| System | Available information |
| --- | --- |
| `report_text_only` | Extracted report claims and numerical range checks |
| `claim_plus_supplied_metrics` | Report claims plus author-supplied metric values |
| `artifact_aware_audit` | Metrics, predictions, split files, and notebook data flow |
| `graph_certified_audit` | Artifact audit plus certificate and graph integrity verification |

## Frozen controlled matrix

The deterministic v1 matrix has 19 cases: 12 injected defects, 7 negative
controls, 6 defect families, and 7 clean-control families. Defects cover invalid
claim ranges, claim/evidence mismatch, forged supplied metrics contradicted by
predictions, exact/normalized/group split overlap, direct notebook test fitting,
and three graph-integrity attacks. Controls cover tolerances, percentage
representation, clean predictions, disjoint splits, seeded notebooks, and an
untouched graph.

Run:

```bash
reprocheck ablation --output outputs/evidence-ablation.json
```

| System | Defects detected | False alarms | Sensitivity | Specificity | Balanced accuracy | Complete family coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Report text only | 1/12 | 0/7 | 8.3% | 100% | 54.2% | 16.7% |
| Claim + supplied metrics | 3/12 | 0/7 | 25.0% | 100% | 62.5% | 33.3% |
| Artifact-aware audit | 9/12 | 0/7 | 75.0% | 100% | 87.5% | 83.3% |
| Graph-certified audit | 12/12 | 0/7 | 100% | 100% | 100% | 100% |

Wilson 95% intervals are stored in the result. The graph-certified sensitivity
interval is 75.75%-100%; its specificity interval is 64.57%-100%. These wide
intervals are important: the observed 100% is not a population guarantee.

Correctness is paired by case. Exact two-sided McNemar results for adjacent
layers are:

| Comparison | Improvements | Regressions | p-value |
| --- | ---: | ---: | ---: |
| Text to supplied metrics | 2 | 0 | 0.5 |
| Supplied metrics to artifact-aware | 6 | 0 | 0.03125 |
| Artifact-aware to graph-certified | 3 | 0 | 0.25 |

Only the middle comparison reaches 0.05 on this small matrix. The graph result
demonstrates three additional integrity capabilities, but does not yet establish
a statistically significant general advantage.

## Exact boundary

The matrix proves that the implemented systems behave as specified on these
declared deterministic cases. It does not estimate defect prevalence, measure
performance on unseen papers, replace expert review, or establish that every
possible leakage and provenance attack is detected. The controlled matrix was
designed and implemented by the project author, so it is development evidence.

A real blind extension requires two external reviewers. The executable packet
and scorer are described in `benchmarks/external_review/README.md`.
