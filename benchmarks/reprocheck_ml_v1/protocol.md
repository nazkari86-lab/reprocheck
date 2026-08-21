# Frozen ReproCheck-ML experiment protocol

This directory defines the experiment before hidden labels are opened. The primary unit
is a repository owner, not a sentence. Owners and project lineages cannot cross train,
validation, test, or prospective cohorts.

The deterministic ReproCheck 0.30.4 rules are prior work and the primary baseline. The
confirmatory system adds learned claim discovery and evidence ranking, hard evidence
constraints, and a threshold selected on validation only. Test is run once after model,
corpus, split, calibration, and evaluator hashes are frozen. Prospective repositories are
acquired only after that freeze.

Passing requires all preregistered conditions in `protocol.json`; a small cohort is
reported as `insufficient_sample`, not as success. English, Russian, Kazakh, and domain
results are always reported separately. All exclusions and failures remain in the public
record.
