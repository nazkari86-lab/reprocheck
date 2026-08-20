# Evidence Trial v19 operator guide

Status: protocol and implementation scaffold. No external v19 result exists yet.

1. Run the offline gate; the 20 deterministic GitHub search frames are in `sources.json`.
2. Build the frozen 0.30.0 wheel and create `registration.json` once.
3. Verify registration immediately before acquisition.
4. Acquire sources once, preserving every raw response and failure manifest.
5. Apply the minimum-information gate. `insufficient_sample` is a valid outcome.
6. If eligible, distribute only the public review packet to two independent humans.
7. Adjudicate all disagreements, lock gold, freeze all three arm outputs, then score once.

Never edit a registered protocol, evaluator, acquisition script, source configuration,
analysis script, or exclusion registry. Never manufacture reviewers or describe the
design as an observed external result.
