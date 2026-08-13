# Upstream discovery v5: preregistered external-generalization study

## Objective

Estimate whether the public ReproCheck 0.21.0 claim extractor can recover
numeric before/after corrections in previously unseen, independently owned
GitHub repositories. This is a source-unseen evaluation, not a population
estimate for all software projects.

## Frozen evaluator

- version: `0.21.0`
- source commit: `96e0a4688ef74e6ddc41ec78471276954c5cda66`
- wheel: `evaluator/reprocheck-0.21.0-py3-none-any.whl`
- wheel SHA-256: `50e9858be7876cab91575670c6cf9d6bd39cc910fce894e2eedd2633693faa34`

The wheel and this protocol must be committed and pushed before retrieval.
Neither the wheel nor the extraction code may be changed before the frozen
zero-shot result is written and checksum-locked.

## Discovery strata

Twenty-four fixed GitHub pull-request searches cover four semantic strata:

1. benchmark/report corrections;
2. performance, latency, and memory corrections;
3. ML/IR metric corrections;
4. evaluation, ground-truth, and documentation synchronization corrections.

Every query includes `is:pr is:merged created:>=2024-01-01` and searches title
and body. The exact strings live in `retrieve.py` and are hash-bound by the
registration.

For every frame, request the first 100 GitHub Search API results, remove every
PR exposed by the prior v2-v4 frames or retrospective discovery manifests, and
sort remaining candidates by SHA-256 of
`reprocheck-upstream-v5|repository#number`. Select the first 20 candidates while
enforcing a global maximum of one selected PR per repository owner and one per
repository. No replacement is performed when a frame has fewer than 20.

The maximum sample is 480 PRs. Frame-level results and raw API responses remain
separate so yield and overlap are auditable.

## Eligibility, labeled without ReproCheck output

A PR is eligible only when all conditions hold:

- it changes a human-readable report artifact (`.md`, `.rst`, `.txt`, `.json`,
  `.csv`, `.tsv`, `.yaml`, `.yml`, or `.html`);
- at least one explicit numeric empirical result changes;
- old and new values describe the same intended system, dataset, split,
  configuration, and metric definition;
- the change corrects a stale, wrong, misparsed, or misreported value rather
  than reporting a new experiment, new product version, new dataset, or changed
  configuration;
- both parent and merge-commit artifacts are public and immutable;
- a unique before snippet and a unique after snippet can ground each selected
  primary claim.

Every sampled PR receives an inclusion/exclusion record. Eligibility decisions,
claim snippets, metric identifiers, and values are frozen before importing or
running either the installed or source-tree ReproCheck parser.

## Primary endpoints

- complete-case visibility: every selected claim is recovered in both before
  and after artifacts;
- claim visibility: selected before/after claim pairs recovered;
- exact source integrity;
- breadth by independent owner, repository, artifact format, language, and
  metric family;
- Wilson 95% confidence intervals for case and claim visibility.

Case visibility is primary. Claim visibility is secondary because claims from
the same repository are correlated.

## Raw-evidence extension

When an eligible PR points to immutable row-level predictions, per-run results,
logs, or machine-readable aggregates at the merge commit, those artifacts will
be selected and frozen before the evaluator runs. A verifier that does not
import ReproCheck will recompute report values where feasible. Availability is
reported; missing raw evidence does not make a report correction ineligible.

## Analysis boundary

Results generalize only to these query-conditioned correction strata. The
one-owner cap improves independence but does not create a probability sample.
Post-inspection fixes, if any, are development evidence and must never replace
the frozen 0.21.0 result. No single composite score will hide case count,
confidence intervals, format breadth, or raw-evidence coverage.
