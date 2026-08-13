# LO3.4 Evaluation of results (apply criteria and interpret)

This section applies the criteria defined in evaluation_criteria.md and
communicates what the results mean, including limitations and next steps.

## A) Requirements coverage evaluation
Metric results:
- % requirements covered by >= 1 passing test: 100% (17/17)
- Highlight requirements covered by system/integration tests: 88.24% (15/17)

Interpretation:
- All LO1 requirements have at least one passing planned test ID.
- Two requirements (R-ROBUST-PARSER-01, R-QUAL-TESTABILITY-01) are covered
  only by unit/review techniques; this is acceptable because these
  requirements concern parser robustness and design seams rather than
  end-to-end system behavior.
- No requirements are deferred or uncovered in the current evidence set.

## B) Structural coverage evaluation (line + branch)
Metric results:
- Overall line coverage (all modules): 53.54%
- Overall branch coverage (all modules): 29.26%
- Core-module (parser/validation/service/sqlite) unweighted average:
  85.11% line, 73.46% branch
- CLI coverage: 0% line/branch (subprocess execution)

Interpretation:
- The overall coverage numbers are pulled down by CLI subprocess execution
  (coverage cannot attribute subprocess lines) and by non-core modules.
- The core in-process modules achieve substantially higher coverage,
  indicating good structural exercise of business logic paths.
- The core-module averages align with risk-based targets in
  evaluation_criteria.md and are supported by strong oracles (explicit
  error codes, invariants, and contract checks).
- Uncovered regions are primarily defensive or exceptional paths:
  - service.py: defensive error mapping for unexpected repository errors.
  - sqlite.py: rollback and cleanup paths triggered by low-level DB
    exceptions not induced in LO3 runs.
  - sqlite.py: defensive branches for malformed rows or missing fields.
  These paths are lower-risk in normal operation; covering them would
  require fault injection or DB error simulation in LO4, alongside
  statistical characterization.

## C) Combinatorial evaluation
Metric results:
- Category coverage: 100%
- Pairwise coverage (bounded subset): 100%

Interpretation:
- The combinatorial plan targets interactions between mobile formatting,
  message validity classes, and auth correctness because these inputs
  influence validation and error-code mapping at the CLI boundary.
- The generated set enumerates the full cross-product of the bounded
  subset (mobile_class × message_class × auth_class, 60 cases), and
  pairwise coverage is reported as the adequacy metric for interaction
  coverage.
- Constraints exclude only impossible combinations (e.g., empty message
  with a valid order payload), ensuring all generated cases are relevant.
- No interaction-specific failures were observed in the current run.

## D) Model-based evaluation
Metric results:
- State coverage: 100% (3/3)
- Transition coverage: 100% (7/7)

Interpretation:
- Critical transitions include place (S0->S1), fulfill with auth success
  (S1->S2), and fulfill with auth failure (S1->S1) because they encode
  safety (no unauthorized transition) and liveness (pending->fulfilled).
- No defined transitions are missing from coverage; the minimal FSM
  intentionally omits error-handling detail, which is covered by the
  functional and CLI contract tests.
- The model adds behavioral-space assurance by exercising state
  progression independently of input partitioning.

## E) Yield evaluation
Metric results:
- Defect yield per technique: no defects recorded in the LO3 evidence run
- Error-code yield: 8 distinct codes exercised out of 11 defined codes
  (72.73% exercised; unexercised codes: ORDER_ALREADY_FULFILLED,
  INTERNAL_ERROR, DATABASE_ERROR)

Interpretation:
- The lack of failures indicates stability at this stage, but does not
  imply that tests are weak; assertions use explicit error codes,
  invariants, and CLI contract checks.
- Failure-mode coverage is treated as a yield proxy: the denominator is
  the defined error-code set in src/orderflow/validation.py (11 constants)
  and the corresponding exit-code handling in src/orderflow/cli.py and
  docs/cli_contract.md, not an exhaustive defect universe. Unexercised
  codes highlight negative partitions to consider in future runs.

## Performance note (LO3 vs LO4)
LO3 includes baseline smoke evidence only.
Formal statistical characterization and target evaluation occur in LO4.

Derived throughput (batch):
- Batch size is fixed at 2 lines in the smoke sample.
- Formula: lines/sec = 2 / (ms / 1000) = 2000 / ms
- Mean/p95 throughput: 36.099 / 37.141 lines/sec
  Source samples_ms are taken from docs/lo3/artifacts/performance_smoke.json.
  Throughput is computed per-sample as 2000 / ms_i for each latency
  measurement (fixed 2-line batch), and mean/p95 throughput are computed
  over the derived throughput samples (not from the inverse of mean/p95
  latency).
