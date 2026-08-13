# ReproCheck 0.21.0

Version 0.21.0 expands prospective natural-error evidence and adds bounded
support for metric layouts found in six independent upstream repositories.

## Source-unseen v4 evidence

Before retrieval, v4 froze ten GitHub search frames, a deterministic first-25
sampling rule, 819 prior exposures, and the public 0.20.0 wheel. It sampled 250
new merged pull requests and labeled eligibility without running ReproCheck.
Six strict like-for-like report corrections were eligible.

The frozen 0.20.0 evaluator recovered 0/6 complete cases and 3/96 initially
selected claims. That result and its evaluator wheel are checksum-locked. Three
MRR labels were later excluded by a public adjudication because the selected
snippet was an unchanged formula row containing neither target value; the
original labels and frozen result were not rewritten.

The post-inspection 0.21.0 parser recovers 6/6 cases and 93/93 valid claims. It
adds general support for:

- ranked metrics and latency in row-labeled Markdown tables, including a
  non-English `Метрика` header and per-system context;
- success/partial/fail rates, coverage, resource deltas, signed percentages,
  and thousands separators;
- ranked metrics in prose, including corrected arrow targets;
- transposed scenario-by-system metric tables;
- peak RSS values with runtime context and feature counts embedded in model
  labels;
- separability deltas.

The implementation contains no repository, pull-request, filename, or expected
numeric-value special cases. New negative and regression tests retain strict
metric-header and known-family boundaries.

## Raw evidence

Three eligible corrections were independently checked below the report layer:

- Popoto: four aggregates recomputed from 1,986 question rows;
- Lore: rates and means recomputed from 390 runs per arm across six repositories;
- SESTRAV: feature mode checked across 35,555 predictions and metrics checked
  against the committed comparison CSV.

All nine immutable raw artifacts are commit-addressed and SHA-256 locked. The
verification script does not import or run the ReproCheck parser.

## Boundary

Claim recovery is 93/93 (Wilson 95% lower bound 96.0%). Case recovery is 6/6,
but its Wilson lower bound is only 61.0% because there are six eligible cases.
The ten GitHub frames are query-conditioned, and only three cases have raw
evidence replay. Therefore this release establishes complete recovery of the
fixed cohort, not universal 10/10 external validity.
