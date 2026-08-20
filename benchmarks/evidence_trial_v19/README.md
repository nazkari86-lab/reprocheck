# Evidence Trial v19 operator guide

Status: preregistered acquisition complete; independent source-only curation pending.
No scored external v19 result exists yet.

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

## Human workflow

The three local browser tools store unfinished work only in that browser's
`localStorage`; the server never writes labels. Each tool validates the complete export
before download and emits a separate hash-bound attestation.

Start source-only curation:

```bash
uv run python benchmarks/evidence_trial_v19/curation_app.py
```

For a curator who should not receive the repository, build the deterministic offline
handoff instead:

```bash
make evidence-trial-v19-curator-handoff
```

The ZIP contains only the source-only app, guide, outcome-blind packet, and 60 verified
frozen source files. It contains its own SHA-256 manifest and runs with plain Python
3.11+; no package installation or network access is required.

After the independent curator exports `enrollment.json`, build and gate the sample:

```bash
uv run reprocheck trial-build-sample \
  --candidates benchmarks/evidence_trial_v19/acquisition-v5/candidates.json \
  --enrollment enrollment.json \
  --output sample.json
uv run reprocheck trial-validate-sample \
  --protocol benchmarks/evidence_trial_v19/protocol.json \
  --sample sample.json \
  --exclusions benchmarks/evidence_trial_v19/exclusions.json
uv run reprocheck trial-prepare-review --sample sample.json --output-dir review
```

Only if the pre-review gate says `eligible_for_blinded_review`, give
`review/public/packet.json` separately to two independent reviewers. Each reviewer runs
the tool on their own machine or isolated browser origin:

```bash
uv run python benchmarks/evidence_trial_v19/review_app.py \
  --packet review/public/packet.json --port 8766
```

If their frozen responses disagree, an independent adjudicator runs:

```bash
uv run python benchmarks/evidence_trial_v19/adjudication_app.py \
  --packet review/public/packet.json \
  --reviewer review-reviewer-a.json \
  --reviewer review-reviewer-b.json
```

Then create the immutable gold lock with the two untouched review files and, only when
needed, `--adjudication adjudication.json`. See `REVIEWER_GUIDE.md` for role separation
and handoff checks.

Never edit a registered protocol, evaluator, acquisition script, source configuration,
analysis script, or exclusion registry. Never manufacture reviewers or describe the
design as an observed external result. Do not use project authors, the evaluator author,
or a model prompted with evaluator outputs as the independent curator or reviewers.
