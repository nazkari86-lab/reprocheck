# ReproCheck 0.10.1

Version 0.10.1 hardens release provenance without changing audit behavior,
claim extraction, metric recomputation, leakage checks, or frozen scientific
results from 0.10.0.

- Generates keyless Sigstore/SLSA provenance for the wheel, source archive,
  and checksum manifest using the official GitHub attestation service.
- Documents independent `gh attestation verify` and SHA-256 verification before
  installation.
- Pins every third-party GitHub Action to a full immutable commit SHA while
  retaining the reviewed release version in a comment.
- Adds a pinned `pip-audit` CI job and repeats the vulnerability audit before
  release publication.
- Adds weekly grouped Dependabot checks for Python and GitHub Actions.
- Adds regression tests that reject mutable workflow action references or
  missing attestation permissions and subjects.

Build provenance proves which repository workflow produced an artifact. It is
not a code-quality guarantee, a trusted scientific result, or a substitute for
reviewing the source and published evaluation protocol.
