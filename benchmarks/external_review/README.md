# External blind annotation protocol

This protocol closes the infrastructure gap but does not pretend that external
reviews have already happened.

## 1. Prepare

```bash
reprocheck review-prepare \
  --corpus benchmarks/holdout_v07_artifacts \
  --sample-artifacts 16 \
  --output-dir outputs/external-review-kit
```

The deterministic sample contains eight claim-bearing and eight zero-claim
complete files selected by SHA-256 rank. The packet uses blind IDs. Send only
the generated `public/` directory, which contains:

- `packet.json`
- `packet-sources/`
- one separate reviewer response template

Keep the sibling `private/PRIVATE-gold.json` inaccessible until both reviewers
have completed and frozen their responses. Do not tell reviewers which stratum
each file came from. Never send or archive the whole kit as one reviewer-facing ZIP.

## 2. Independent annotation

Each reviewer must inspect every complete source file and list all in-scope
numerical model-evaluation claims as normalized `metric` and numeric `value`.
They must set `independent_review_confirmed` to `true`. Reviewers must not discuss
cases or inspect ReproCheck output, internal annotations, the evaluator, or each
other's response before freezing.

Recommended reviewers are a teacher/researcher familiar with experimental ML
and a second technically competent reviewer who was not involved in ReproCheck.
Record identities and qualifications outside the public blind packet.

## 3. Freeze and score

Archive both response files and their SHA-256 hashes before revealing gold.
Then run:

```bash
reprocheck review-score \
  --gold outputs/external-review-kit/private/PRIVATE-gold.json \
  --reviewer reviewer-A-frozen.json \
  --reviewer reviewer-B-frozen.json \
  --output outputs/external-review-result.json
```

The scorer reports reviewer-vs-internal precision/recall/F1, exact artifact
agreement, claim-presence Cohen's kappa, and blind IDs requiring adjudication.
The result records SHA-256 for gold and both exact reviewer response files.
Any disagreement must be resolved by a third reviewer who sees both rationales;
the original responses remain immutable.

Preparation refuses a non-empty output directory, and scoring refuses to
overwrite an existing result. Use a new directory or filename for every frozen
review round.

## Scientific boundary

Agreement validates annotation reliability on the selected sample. It does not
turn the already-inspected v0.7 holdout into a new zero-shot evaluator test and
does not prove that the reported claims are scientifically true.
