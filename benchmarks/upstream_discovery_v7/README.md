# Upstream discovery v7

This is the first valid fresh holdout after the 0.22.0 parser changes. It sampled
160 merged pull requests from 160 previously unexposed repository owners. Labels and
immutable sources were frozen and pushed before the parser ran.

Four cases with 11 same-scope corrected claims were eligible. Frozen 0.22.0 recovered
1/4 complete cases and 5/11 claims. The complete VAD table correction was recovered;
the RKNN table was partial; hashfile-size prose and test-count prose were missed.

The exact result is checksum-locked in `results.lock.json`. It is a query-conditioned,
small cohort: 25% case visibility has Wilson 95% interval 4.6%–69.9%, and 45.5% claim
visibility has interval 21.3%–72.0%. These are not population estimates.

After inspecting the misses, development 0.23.0 recovers 3/4 cases and 9/11
claims by adding mean-latency and test-count support. The remaining hashfile-size
case is intentionally represented as `artifact_size_mb`, not mislabeled as memory
merely to raise the score. This post-inspection result is not external validation.
