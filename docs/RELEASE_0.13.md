# ReproCheck 0.13.0

Version 0.13.0 fixes four audit/reporting defects and expands deterministic
evidence matching without introducing model execution or opaque AI decisions.

## Correctness fixes

- Web metric values now use schema metadata: bounded scores are percentages;
  MAE, RMSE, R2, and log-loss remain scalars.
- Exact and additional normalized-only split overlaps produce independent
  findings.
- Group findings report the complete overlap count while retaining at most 100
  examples in the certificate.
- Composite Action paths move through environment variables instead of direct
  shell interpolation.
- Binary asymmetric metrics no longer guess the positive class.

## Evidence graph

Claims extracted from Markdown/HTML tables retain recognized context fields:
model, dataset, split, experiment, task, averaging, threshold, run, and variant.
Wide-CSV selectors carry the same context. Conflicting shared dimensions produce
`no_evidence` rather than comparing a baseline claim with a proposed-model row.
Context fields are optional in schema 1.2, so older certificates remain valid.

An optional `y_score` column adds binary AUROC, AUPRC, log-loss, and Brier score.
The positive label and both classes are mandatory, scores must be finite values
in `[0,1]`, and every numerical convention is recorded in metric evidence.

## Static analysis and ingestion

Notebook analysis adds bounded AST propagation through split outputs, aliases,
containers, and simple same-notebook function wrappers. Saved stream,
`text/plain`, and `text/markdown` notebook outputs become claim text without
executing code. Dynamic Python remains outside the guarantee.

## Supply chain

`uv.lock` pins transitive artifacts and hashes; CI installs its hash-verified
export and `make gate` rejects lock drift. Releases add a runtime CycloneDX SBOM
to checksums and GitHub/Sigstore provenance.
The local web security boundary now explicitly forbids direct public exposure.
