# ReproCheck 0.11.0

Version 0.11.0 improves deterministic lexical near-duplicate detection without
changing claim extraction, metric recomputation, or historical frozen results.

- Adds `hybrid_lexical_v1`, the maximum of token-set Jaccard similarity and
  Unicode character-trigram Dice similarity.
- Uses complete token and trigram inverted indexes plus mathematically safe
  size upper bounds before exact scoring.
- Makes equal-score selection deterministic by preserving train-row order.
- Keeps `token_jaccard` as an explicit legacy mode for prior-result
  reproduction.
- Exposes `text_similarity(left, right, method=...)` in the Python API and
  `--near-method` in the CLI, web form, and project manifest.
- Changes the default near-match threshold from `0.9` to `0.8`; both values and
  the selected method are sealed into each audit certificate.
- Adds a frozen 24-pair English, Russian, and Kazakh controlled benchmark. At
  threshold `0.8`, hybrid lexical matching detects 12/12 mutations and rejects
  12/12 unrelated controls; legacy token Jaccard detects 3/12 mutations and
  rejects 12/12 controls.

The benchmark is synthetic and intentionally tests lexical variation. It does
not establish semantic-paraphrase recall, performance on a natural prevalence
distribution, or superiority to embedding models or human review.
