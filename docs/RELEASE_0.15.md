# ReproCheck 0.15.0

Version 0.15.0 adds the scientific comparison layer required to evaluate the
evidence graph as a method rather than only as an implementation feature.

- `reprocheck ablation` runs 19 paired cases across report-only,
  claim-plus-metrics, artifact-aware, and graph-certified systems.
- The frozen result includes Wilson intervals, defect-family coverage, and exact
  two-sided McNemar comparisons without calling controlled evidence blind.
- `reprocheck review-prepare` creates a deterministic label-hidden packet with a
  separately protected internal answer key.
- `reprocheck review-score` requires two distinct reviewers who explicitly
  confirm independent work and reports agreement plus adjudication needs.
- Related-work and novelty boundaries distinguish ReproCheck from ReproZip,
  Whole Tale, checklist programs, and human artifact badging.

No external reviewer result is claimed in this release. The protocol is ready;
the recorded completed external reviewer count remains zero.
