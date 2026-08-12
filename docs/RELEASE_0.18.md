# ReproCheck 0.18.0

Version 0.18.0 generalizes the canonical minimal witness from one finding to
three strict audit-specific verifier rules.

## Three rule adapters

- `claim_metric_mismatch.source_grounded.v2` binds report claim, contradictory
  observation and both source artifacts.
- `metric_evidence_conflict.source_grounded.v1` binds two conflicting metric
  observations to their distinct sources without relying on source-list order.
- `exact_split_overlap.artifact_recomputed.v1` binds train/test artifacts and
  independently reopens their CSV bytes to recompute exact identity overlap.

Legacy canonical v1 mismatch witnesses remain verifiable. Unsupported findings,
missing artifacts, ambiguous bindings, changed CSV bytes, malformed numeric
values and noncanonical candidates fail closed.

## Evidence

The controlled benchmark contains 12 author-designed cases, four per rule. The
exact witnesses reduce nodes by 68.9% and serialized bytes by 77.8% relative to
the complete evidence graphs; 48/48 controlled tamper variants are rejected.

The separate source-derived benchmark contains 30 cases: 27 deterministic
controlled mutations of Iris, Diabetes and YOLO frozen experiment artifacts,
plus three unchanged negative controls. Expected witness construction,
independent verification, tamper rejection and control specificity are 100% on
this declared matrix. Natural defect cases are zero.

These results establish bounded implementation behavior. They do not estimate
natural defect prevalence, cross-project generalization or human reviewer time
savings.

## Demonstration

`make rknp-demo` now builds and independently verifies one witness per rule,
runs both witness benchmarks and preserves the earlier evidence-layer ablation.
