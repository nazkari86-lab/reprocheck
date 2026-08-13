# Upstream discovery v5

This study measures whether ReproCheck can see like-for-like numeric corrections in
previously unseen, merged GitHub pull requests. It contains no generated or synthetic
claims: every selected claim is copied from an immutable public before/after source.

The protocol, 24 search frames, global one-owner cap, prior-exposure exclusions, frozen
0.21.0 wheel, and maximum sample size were committed before retrieval. The deterministic
sample contains 432 pull requests from 432 independent repository owners. All candidates
were blind-labeled without ReproCheck output. Eleven cases (34 changed claims) met the
strict eligibility rules.

The immutable zero-shot result is deliberately retained even though it failed: frozen
0.21.0 found 0/11 complete cases and 0/34 claims. After inspecting those failures, the
development parser finds 11/11 cases and 34/34 claims. The latter is correction evidence,
not an independent external-validation result. A fresh source-unseen study is required to
measure whether the added format support generalizes.

Run:

```bash
python3 benchmarks/upstream_discovery_v5/verify_study.py
```

The cohort is query-conditioned and has a low eligibility yield. Neither score is a
population-wide recall estimate for all scientific repositories.
