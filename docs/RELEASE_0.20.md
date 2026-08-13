# ReproCheck 0.20.0

Version 0.20.0 adds a second prospectively registered, source-unseen natural
correction study and bounded parsing support for two formats that the frozen
0.19.0 release completely missed.

## Prospective evidence

Five precommitted GitHub queries yielded 484 new candidates after 335 prior
exposures were excluded. A deterministic digest selected 150 PRs, all labeled
before either parser ran. Two like-for-like corrections were eligible, with 32
numeric old/new claims in immutable Markdown and JSON pairs.

The frozen 0.19.0 wheel recovered 0/2 cases and 0/32 claims. That zero-shot
result is checksum-locked. The post-inspection 0.20.0 parser recovers 2/2 cases
and 32/32 claims by adding:

- strict row-labeled retrieval tables (`Metric`/`Measure`, known metric@k only);
- structured `swebench` score keys without silently converting their native
  0-100 scale.

Negative tests reject unknown row metrics and tables without an explicit metric
header. The implementation generalizes by format; it contains no repository,
PR, filename, or expected-value special cases.

The gate also stops regenerating v2's checksum-locked historical 0.19.0 result
with a newer package version. It now verifies that immutable record in place;
the current parser is regenerated and locked only by v3.

## Boundary

The 0.20.0 result is development evidence on failures already inspected, not a
new unseen holdout. Only two eligible cases were found, the search frame is not
a probability sample, and neither case includes independently frozen raw
experimental evidence. The release demonstrates complete recovery of this
fixed cohort, not universal recall or 10/10 external validity.
