# ReproCheck 0.12.0

Version 0.12.0 adds order-sensitive leakage screening, a public indexed-search
API, and the project's first independently labelled holdout for lexical methods.

## Algorithm and API

- `ordered_tokens_v1` compares normalized token sequences rather than token
  sets, making meaning-changing reordering visible.
- `find_text_matches(train_texts, test_texts, threshold=..., method=...)`
  exposes the complete indexed join and returns match indices, similarities,
  exhaustive pairs, candidates, and expensive scores.
- A mathematically safe token-multiset upper bound prunes sequence comparisons
  without changing exhaustive-search results.
- CLI, web, and project-manifest inputs support the ordered method while
  preserving `hybrid_lexical_v1` as the default typo-oriented mode.

## Preregistered PAWS result

The methods, thresholds, evaluator SHA-256, source revisions, hypothesis, and
statistics were published in commit
`2f2ec247ce55fd1efadee27d42c3814186c289d9` before downloading the PAWS-Wiki
test content. The single locked run contains 8000 independently labelled test
pairs.

`ordered_tokens_v1` reached 70.53% balanced accuracy versus 54.94% for
`hybrid_lexical_v1`, an improvement of 15.58 percentage points. The exact
two-sided McNemar result is `p = 7.07e-143`. Ordered-token precision is 66.20%
and recall is 68.92%, so this is meaningful improvement rather than solved
semantic matching. The validation-trained logistic comparator reached 66.48%
balanced accuracy on test.

PAWS is English-only and asks whether a pair is a semantic paraphrase. It is a
useful adversarial test of order sensitivity, not a direct estimate of leakage
prevalence, Kazakh/Russian quality, or performance against embedding models.

## Scalability boundary

The deterministic scalability suite reduces 10,000,000 sparse-corpus pairs to
51,548 candidates and 500 sequence scores. In an adverse common-token corpus,
candidate reduction is 0%, while the multiset bound reduces 400,000 sequence
scores to 100. Wall-clock speed remains environment- and corpus-dependent.
