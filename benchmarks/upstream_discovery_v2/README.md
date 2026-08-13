# Prospective upstream discovery v2

This study removes parser readability from eligibility. The retrieval protocol
and evaluator revision were committed before the first GitHub API request.

## Frozen evidence

- 298 unique candidates returned across three query-conditioned frames.
- 75 pull requests selected by a deterministic SHA-256 rank (25 per frame).
- 75/75 inspected without running ReproCheck; every exclusion has a reason.
- 3 natural, like-for-like corrections were eligible, from 3 repositories and
  3 independent owners.
- 15 old/new numeric claims were selected from 16 immutable source files.
- Frozen ReproCheck 0.18.0: 0/3 exact-visible cases and 0/15 exact-visible
  claims.
- Post-inspection development parser: 3/3 cases and 15/15 claims.

The case-level development Wilson 95% interval is 43.85%-100%; the claim-level
interval is 79.61%-100%. These intervals are wide and describe only the frozen,
query-conditioned sample. No case has independently frozen raw experimental
evidence beyond the corrected publication pair, so raw-evidence agreement is
not estimated for this cohort.

Run `make upstream-discovery-v2` to regenerate the development result and
verify the registration, sample, labels, raw responses, immutable sources,
zero-shot result, and development result against their locks.
