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
4. The `test` split may be evaluated exactly once. The evaluator refuses to
   overwrite its locked output, including an unfavourable result.

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
```

The source files are ignored by Git. Their byte sizes and SHA-256 digests are
fixed in `source-manifest.json`.
