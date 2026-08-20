# Evidence Trial v19 blinded review and adjudication

## Separation of roles

Two reviewers independently label every claim. They must not receive ReproCheck arm
predictions, gold labels, the other reviewer's response, or desired class counts. Each
uses a stable non-identifying ID and confirms independence from the evaluator, curator,
and sampled repository authors. Reviewer files must be frozen before comparison.

The three verdicts have fixed meanings:

- `supported`: cited evidence verifies the claim;
- `contradicted`: cited evidence conflicts with the claim;
- `not_verifiable`: available evidence cannot decide the claim.

Every decision requires a substantive rationale and at least one evidence reference.
Run the guarded interface against the exact public packet:

```bash
uv run python benchmarks/evidence_trial_v19/review_app.py \
  --packet review/public/packet.json --port 8766
```

Use separate machines or isolated origins for the two reviewers. Do not reuse another
reviewer's browser storage. Preserve each exported review and attestation byte-for-byte.

## Adjudication

Only after both reviews are frozen may an independent adjudicator see the two responses.
The adjudicator sees only disagreements, reviewer evidence, and the original public
claim; evaluator predictions remain unavailable.

```bash
uv run python benchmarks/evidence_trial_v19/adjudication_app.py \
  --packet review/public/packet.json \
  --reviewer review-reviewer-a.json \
  --reviewer review-reviewer-b.json
```

If there are no disagreements, the tool exits successfully and no adjudication file is
created or passed to `trial-lock-gold`. Otherwise it requires every disagreement to be
resolved exactly once and exports `adjudication.json` plus a separate attestation.

## Gold lock

```bash
uv run reprocheck trial-lock-gold \
  --review-dir review \
  --reviewer review-reviewer-a.json \
  --reviewer review-reviewer-b.json \
  --adjudication adjudication.json \
  --output gold.json
```

Omit `--adjudication` only when reviewer verdicts agree on every claim. The gold lock is
not a scored result; the registered three arm outputs must still be frozen and scored
exactly once under the preregistered protocol.
