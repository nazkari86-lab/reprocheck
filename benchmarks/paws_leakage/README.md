# PAWS leakage study

This benchmark tests lexical overlap methods on the independently labelled
PAWS-Wiki paraphrase task. It is deliberately stricter than ReproCheck's
operational near-duplicate screening: high lexical overlap can represent either
a paraphrase or a meaning-changing word-order adversary.

## Scientific protocol

1. `validation` is the only development split. It selects every threshold on a
   fixed 0.001 grid and trains the exploratory logistic comparator.
2. `preregistration.json` freezes methods, thresholds, metrics, hypotheses, and
   the expected test hash before the test file is downloaded.
3. `preregistration.lock.json` hashes the evaluator, source manifest,
   development result, and registration. Run `python verify_registration.py` to
   verify the lock.
4. The `test` split was evaluated exactly once after the preregistration was
   published in commit `2f2ec247ce55fd1efadee27d42c3814186c289d9`. The evaluator
   refuses to overwrite its locked output, including an unfavourable result.

## Locked result

On 8000 unseen test pairs, `ordered_tokens_v1` reached 70.53% balanced
accuracy, compared with 54.94% for `hybrid_lexical_v1`: a preregistered
improvement of 15.58 percentage points. The exact two-sided McNemar test has
`p = 7.07e-143` (2247 pairs correct only for ordered, 854 only for hybrid).

This is a statistically strong improvement, not near-perfect classification:
ordered-token precision is 66.20% and recall is 68.92%. The best result among
the frozen comparators is ordered tokens; the validation-trained logistic
baseline reaches 66.48% balanced accuracy on test.

The controlled multilingual typo benchmark remains separate. PAWS measures
semantic paraphrase discrimination in English and must not be presented as a
universal contamination benchmark.

## Reproduce development evidence

```bash
python fetch_sources.py --split validation
python evaluate.py \
  --phase validation \
  --source sources/validation.parquet \
  --output /tmp/paws-validation.json
python verify_registration.py
python verify_locked_test.py
```

The source files are ignored by Git. Their byte sizes and SHA-256 digests are
fixed in `source-manifest.json`.
