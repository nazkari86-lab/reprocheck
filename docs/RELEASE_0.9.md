# ReproCheck 0.9.0

Version 0.9.0 adds a manifest-driven project audit without changing claim
extraction, metric computation, or the frozen scientific results from 0.8.0.

- Adds `reprocheck check reprocheck.json` for one-command multi-experiment
  audits with stable exit codes.
- Publishes fail-closed JSON Schemas for project manifests and linked batch
  certificates.
- Resolves inputs relative to the manifest while rejecting traversal and
  symlink escapes outside the project root.
- Writes outputs only after every experiment succeeds, uses atomic certificate
  replacement, and optionally renders one HTML report per experiment.
- Extends `reprocheck verify` to validate the manifest, nested source files,
  each child certificate, and the aggregate status/digest linkage.
- Adds tamper, malformed-input, duplicate-ID, partial-output, and nested-path
  regression tests.
- Adds a reusable `nazkari86-lab/reprocheck@v0.9.0` composite GitHub Action and
  exercises it end to end in CI before the full scientific gate.

The batch checksum is an integrity certificate, not an author identity
signature. Independent dual annotation of a new unseen corpus remains the
strongest external scientific next step.
