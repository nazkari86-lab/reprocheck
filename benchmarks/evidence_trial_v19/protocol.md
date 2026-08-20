# ReproCheck Evidence Trial v19

This is a prospective, fail-closed comparison of three evidence conditions on the same
blinded public ML claims: report only, supplied metrics, and raw artifact recomputation.

The primary endpoint is contradiction recall. H1 requires raw recomputation to improve
over report-only review by at least 10 percentage points, with a strictly positive 95%
owner-cluster bootstrap lower bound. Raw recomputation must also keep false accusations
at or below 5%. Claims are labelled `supported`, `contradicted`, or `not_verifiable`.

At least two independent reviewers label every claim without access to internal gold.
Every disagreement is adjudicated before an immutable gold lock is created. Natural
claims determine the primary result; controlled mutations are reported separately.

The minimum-information gate is 20 repository owners, 150 natural claims, 20
contradictions, 30 not-verifiable claims, and 30 supported claims with evidence beyond
the report. A shortfall is a valid `insufficient_sample` result and must not be converted
into a success claim.

The certificate track is separate from the three-arm accuracy comparison. It measures
verdict preservation, serialized byte reduction, and rejection of registered tampering.

This trial is bounded to its frozen public-source frame. It does not establish universal
ML reproducibility, causality, or generalization to private artifacts.
