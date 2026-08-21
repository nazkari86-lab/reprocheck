# ReproCheck auxiliary silver experiment v1

Status: **completed auxiliary experiment; not a human-gold evaluation**.

## Question

Can a model distinguish a numerical result block paired with its own source block from
the same claim paired with a result block belonging to another owner in the same domain?

The protocol, implementation, split policy, models, calibration rule, and test policy
were registered and pushed before the test was run. Registration SHA-256:
`65d3fafcb3ef87d29ba73ce456127b2897b83b2153e8523dbd0ddf12609da6ce`.

## Data and split

- 428 balanced claim-evidence pairs from authentic open-source artifacts
- 214 constructed positive and 214 constructed negative pairs
- 59 owners with eligible candidate blocks
- train: 208 pairs, 33 owners
- validation: 102 pairs, 12 owners
- test: 118 pairs, 14 previously unseen owners
- owner-disjoint, domain-stratified split

## Frozen test results

| Method | Precision | Recall | F1 | AUROC | Brier |
|---|---:|---:|---:|---:|---:|
| Claim-only sparse logistic | 0.500 | 1.000 | 0.667 | 0.500 | 0.2500 |
| Evidence-only sparse logistic | 0.515 | 0.898 | 0.654 | 0.524 | 0.2508 |
| Full claim+evidence sparse logistic | 0.712 | 0.712 | 0.712 | 0.845 | 0.2168 |
| Lexical-overlap baseline | 1.000 | 1.000 | 1.000 | 1.000 | 0.0004 |

For the full-pair model, the 1,000-sample owner-level bootstrap 95% interval was
`[0.634, 0.779]` for F1 and `[0.813, 0.908]` for AUROC.

## Interpretation

The full-pair ML model learned cross-text signal: its AUROC was 0.845, while the
claim-only ablation remained at chance (0.500). However, it did **not** beat the simple
lexical-overlap baseline. The positive pair repeats the source block verbatim, making
this auxiliary task easy for deterministic matching. Therefore this experiment proves
that the training and evaluation pipeline works, but it does not establish a scientific
advantage for ML.

This negative result changes the research direction constructively: ML should be tested
on paraphrased claims, incomplete context, value substitutions, multilingual reports,
and evidence located in a different artifact. Those cases require independent human
labels or a separately registered hard-negative benchmark.

## Prohibited interpretation

These values must not be described as ReproCheck accuracy on real scientific claims.
They are performance on automatically constructed silver pairs. Human-gold annotation,
adjudication, hidden evaluation, and prospective evaluation remain incomplete.
