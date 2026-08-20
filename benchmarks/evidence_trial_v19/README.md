# Evidence Trial v19 operator guide

Status: preregistered implementation. No external v19 result exists yet.

1. Run the offline gate; the 20 deterministic GitHub search frames are in `sources.json`.
2. Build the reproducible frozen 0.30.4 wheel and create `registration.json` once.
3. Verify registration immediately before acquisition.
4. Acquire sources once, preserving every raw response and failure manifest.
5. Have a curator independent from the evaluator enroll exact source-line claims with
   `trial-build-sample`; enrollment contains no gold labels.
6. Apply the pre-review owner and claim-count gate. `insufficient_sample` is valid.
7. If eligible, distribute only the public review packet to two independent humans.
8. Adjudicate every disagreement, lock gold, then apply the class-information gate.
9. Freeze all three schema-validated arm outputs and score once. Controlled mutations
   remain secondary and all nine registered certificate tamper classes must be present.

Never edit a registered protocol, evaluator, acquisition script, source configuration,
analysis script, or exclusion registry. Never manufacture reviewers or describe the
design as an observed external result. Do not use project authors, the evaluator author,
or a model prompted with evaluator outputs as the independent curator or reviewers.
