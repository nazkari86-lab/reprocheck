# ReproCheck 0.6.0

## Added

- Markdown and HTML result-table extraction for AP, AP50, AP75, AR, and PQ.
- Scoped detection names including `box_ap`, `mask_ap`, `keypoint_ap`, and
  `proposal_ar`.
- Public `extract_table_claims()` and top-level parser exports.
- Frozen 114-artifact Detectron2/MMDetection challenge corpus with 1,006 labels.
- Versioned challenge JSON Schemas and byte-identical replay from hashed wheels.

## Changed

- Equal values in distinct metric columns remain distinct claims.
- Ambiguous cells containing multiple numeric candidates are skipped rather than
  interpreted using the first number.
- Escaped Markdown pipes no longer shift table columns.
- The 60-artifact baseline is versioned as `baseline-v3.json`; its observed
  40/40 claim result and 130-case mutation/control result are unchanged.

## Evidence

The evaluator frozen before challenge inspection (0.5.0) recovered 18/1,006
labels. The post-inspection 0.6.0 evaluator recovered 1,006/1,006 labels and
emitted two additional valid Average Precision claims omitted by the frozen
rule. Strict precision is 99.80% and recall is 100% on this development corpus.

This is not a held-out accuracy claim. The challenge corpus was used to develop
0.6.0, annotations are rule-derived, and no external annotator or adjudicator
has reviewed them. See `SCIENTIFIC_PROTOCOL.md` for the complete boundary.
