# Evidence Trial v19 source-only curation

The curator must be independent from the ReproCheck evaluator author and from the
authors of the sampled repositories. The curator receives `curation-packet.json` and
the `acquisition-v5/sources/` directory. They must not receive evaluator predictions,
reviewer labels, desired class counts, or any gold-status information.

## Task

Inspect all 60 candidate files. Enroll every explicit empirical ML result claim that can
be bound to an exact contiguous source-line block. Do not select claims because they
look correct, incorrect, reproducible, or unverifiable. Claim completeness takes
priority over reaching a desired outcome balance.

Write one `enrollment.json` object conforming to
`reprocheck.evidence-trial-enrollment.v1`:

- use a non-identifying, stable `curator_id`;
- set `independent_from_evaluator` to `true` only if the condition is genuinely met;
- set `candidate_manifest_sha256` to
  `bf3165d5a2f9fbece966307ab731ae355869bd4a78f76d9f32f0fc87d26d33de`;
- assign unique IDs such as `claim-001`;
- copy `candidate_id` from the packet;
- set `block.start` and `block.end` to 1-based inclusive line numbers;
- copy `claim_text` exactly from those lines, apart from outer whitespace;
- use `natural_unadjudicated` for natural claims; controlled mutations are a separate
  secondary track and must not be invented during curation;
- record `declared_metric` and normalized `declared_value` when a single declared metric
  is explicit, otherwise use `null`;
- set `evidence_tier` from what the frozen source actually supplies: `report_only`,
  `supplied_metrics`, or `raw_recomputation`.

The curator should record ambiguities separately, without assigning a trial outcome.
For the guarded local interface, run:

```bash
uv run python benchmarks/evidence_trial_v19/curation_app.py
```

The interface verifies all 60 frozen source hashes before starting, requires every
candidate to be marked inspected, validates exact source-line text server-side, and
exports `enrollment.json` plus a separate curation attestation. Unfinished work remains
only in browser `localStorage`; the local server does not persist labels.

After delivery, run:

```bash
reprocheck trial-build-sample \
  --candidates acquisition-v5/candidates.json \
  --enrollment enrollment.json \
  --output sample.json
```

Then run `trial-validate-sample`. Before blinded review only the 20-owner and 150-claim
requirements apply. Contradicted, supported-evidence, and not-verifiable minima are
checked only after two independent reviews and complete adjudication.
