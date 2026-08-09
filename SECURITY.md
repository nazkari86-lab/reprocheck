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

The SHA-256 certificate is an integrity checksum, not an authenticated digital
signature. It detects payload or artifact changes but does not prove author
identity or trusted timestamping.
