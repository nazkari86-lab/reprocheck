# ReproCheck-ML benchmark

Status: **the registered development corpus has been materialized; independent human
annotation and all ML performance results remain incomplete.** Do not claim model
performance until the registered experiment is completed.

The first metadata-only discovery is preserved as an imbalanced pilot and is not the
confirmatory cohort. See `amendment-001.md`. The replacement v2 discovery is registered
separately and requires exactly 40 owners in each domain before repository contents are
opened.

Workflow:

1. Freeze `protocol.json`, `source-frame.json`, `exclusions.json`, schemas, and scripts
   with `python register.py --output registration.json`.
2. Verify the lock with `python verify-registration.py registration.json`.
3. Run `python acquire.py discover --output discovery.json` to acquire immutable
   repository heads from the frozen search frames and record every metadata exclusion.
4. Run `python acquire.py verify-discovery --discovery discovery.json` before inspecting
   repository contents.
5. Materialize supported report/evidence files, then annotate independently, adjudicate
   disagreements, and validate source spans/hashes.
6. Build the owner-disjoint split and reject exact/near leakage.
7. Train on `train`, calibrate on `validation`, then freeze the model.
8. Run hidden `test` once. Acquire prospective owners only afterward.

The scripts are thin, auditable entry points to the tested package functions. See the
project design document for annotation, review, and reporting details.

## Materialized development corpus

The balanced v2 cohort was materialized on 2026-08-21 after its selection rules and
transport amendment were published. The immutable result contains 120 repositories
(40 computer vision, 40 NLP, 40 other ML), 1,007 UTF-8 artifacts, and 13,141,967 bytes.
Its materialization SHA-256 is
`521b4b7f2f7c6f4e6560cd9a9139e9fd0ccc780ab6055255136e97d8c77a1475`.

This is an authentic unlabeled corpus, not evidence that the classifier works. Of the
selected artifacts, 997 are report documents and 10 are structured metric artifacts.
Every local file is bound to its source repository, frozen commit, blob SHA, byte size,
and content SHA-256 in `data/materialized-development-v1/materialization.json`.

## Auxiliary ML result

A preregistered owner-disjoint silver experiment has now been completed. The full-pair
sparse logistic model reached test F1 `0.712` and AUROC `0.845`, but a lexical-overlap
baseline reached `1.000` on the constructed task. This is a useful negative result: it
verifies the training pipeline while showing that the current silver task is too easy to
demonstrate an ML advantage. See `silver-experiment-report-v1.md`. Human-gold performance
is still unknown.

A second preregistered mechanism experiment tested single-number substitutions while
holding the surrounding evidence text nearly constant. On 150 balanced test pairs from
unseen owners, the hybrid numeric-consistency model reached F1 `0.933` and AUROC `0.960`,
versus F1 `0.631` / AUROC `0.496` for text-only ML. This supports the hybrid architecture
but remains a constructed mutation result, not human-gold accuracy. See
`mutation-experiment-report-v2.md`.
