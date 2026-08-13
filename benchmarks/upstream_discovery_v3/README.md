# Prospective upstream discovery v3

This is a source-unseen test of the frozen ReproCheck 0.19.0 wheel. The five
GitHub queries, exclusion universe, deterministic sampler, evaluator wheel, and
eligibility rule were committed and pushed before retrieval.

## Evidence

- 484 unique candidates remained after excluding 335 previously exposed PRs.
- 150 PRs were selected deterministically, 30 from each query frame.
- All 150 were labeled without running either the frozen or development parser.
- Two natural like-for-like corrections were eligible, from two repositories
  and two independent owners.
- The immutable pairs contain 32 selected old/new claims: 31 retrieval metrics
  in a row-labeled Markdown table and one SWE-bench score in JSON.
- Frozen 0.19.0: **0/2 cases and 0/32 claims** exactly visible.
- Post-inspection 0.20.0: **2/2 cases and 32/32 claims** exactly visible.

The development result is not another unseen test. Its case-level Wilson 95%
interval is 34.24%-100% and its claim-level interval is 89.28%-100%. Both are
conditional on the frozen query frame. Neither case has independently frozen
raw experimental evidence, so raw-evidence agreement is not estimated.

Run `make upstream-discovery-v3` to reproduce the development result and verify
the registration, raw API bytes, sample, labels, immutable sources, frozen
zero-shot result, and development lock.
