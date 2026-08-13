# Independent cross-project holdout v12

This study prospectively evaluated frozen ReproCheck 0.26.0 at commit
`0b52ada` on public result documents from owners excluded from every prior
discovery and cross-project holdout.

The query, sampling, eligibility, annotation, precision endpoint, evaluator,
and success thresholds were committed and pushed before retrieval. All 62
retrieved documents came from different owners. Manual review exhausted the
sample and found 20 eligible documents with 190 gold claims. Sources and labels
were committed and pushed at `585edb9` before the evaluator was run.

## Immutable zero-shot result

- complete documents: 1/20 (5.0%);
- claim recall: 26/190 (13.68%), 95% Wilson CI 9.51%-19.30%;
- block precision: 26/41 (63.41%), 95% Wilson CI 48.12%-76.41%;
- false negatives: 164;
- false positives: 15;
- preregistered success: **false**.

The immutable result is `results/zero-shot-0.26.0.json`, SHA-256
`1a8938f686caea152bc0d5bb8025886fa5633abc272f8c56560c4c8e2a1d5ad5`.

This result is negative external-generalization evidence. Post-result label
audits, parser changes, corrected analyses, or development scores must remain
separate and cannot replace this zero-shot result.

