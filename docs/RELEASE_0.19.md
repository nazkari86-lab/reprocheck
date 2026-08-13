# ReproCheck 0.19.0

Version 0.19.0 adds a prospectively registered natural-correction discovery
study and fixes every parser failure observed in its eligible cohort.

## Prospective evidence

The protocol, exact GitHub queries, deterministic SHA-256 sampler, and evaluator
revision were committed before retrieval. Three query-conditioned frames
returned 298 unique candidates; 75 pull requests were selected and all 75 were
labeled without using ReproCheck output. Three natural like-for-like corrections
were eligible, containing 15 selected numeric claims in 16 immutable files.

Frozen 0.18.0 recovered 0/3 cases and 0/15 claims. That result remains locked.
The post-inspection 0.19.0 parser recovers 3/3 cases and 15/15 claims on the same
unchanged cohort by adding bounded support for generic score reports, structured
measurement keys, and validator-count methodology prose.

## Boundary

This is development evidence, not a new unseen holdout. The case-level Wilson
95% interval is 43.85%-100%, and the three search frames are not a probability
sample of GitHub. No independently frozen raw experimental evidence is available
for these three cases. The release therefore does not claim universal recall,
defect prevalence, or 10/10 external validity.

Run `make upstream-discovery-v2` for the locked replay and `make gate` for the
complete local verification suite.
