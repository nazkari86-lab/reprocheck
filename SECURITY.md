# Security policy

ReproCheck v0.6 treats all uploads as untrusted data. The web application limits
each upload to 20 MB, stores it in a temporary directory, and never executes
uploaded scripts or notebooks.

DOCX expanded content is capped at 100 MB and PDF reports at 1000 pages.
Certificate verification rejects path traversal, malformed digests, malformed
sizes, and duplicate artifact descriptors. CPU-heavy audits run outside the
FastAPI event loop.

Do not add notebook execution directly to the web process. A future execution
worker must use an isolated container with no network access, a read-only base
filesystem, a non-root user, CPU/memory/time limits, and disposable storage.

The built-in SHA-256 certificate is an integrity checksum, not an authenticated
digital signature. ReproCheck can add a detached Ed25519 signature using an
encrypted private key. That signature proves possession of the corresponding
private key; author identity is established only when the public key or its
fingerprint is authenticated through an independent trusted channel. ReproCheck
does not provide trusted timestamping. Never commit a private signing key or
its password.

Official release assets also carry GitHub-hosted Sigstore/SLSA provenance.
Verify it with `gh attestation verify` as documented in
`docs/REPRODUCIBILITY.md`; SHA-256 alone detects changed bytes but does not
establish which workflow produced them.
