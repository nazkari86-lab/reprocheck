# ReproCheck 0.10.0

Version 0.10.0 adds optional authenticated signatures without changing claim
extraction, metric recomputation, leakage checks, or the frozen scientific
results from 0.9.1.

- Adds encrypted Ed25519 key generation with private-key mode `0600` on POSIX.
- Adds detached signatures over the exact certificate bytes with domain
  separation and a strict published JSON Schema.
- Adds fail-closed verification of the certificate, linked artifacts, detached
  envelope, signature, and separately supplied trusted public key.
- Reads private-key passwords only from an environment variable, never from a
  command-line argument.
- Exposes the signing operations through both the CLI and lazy Python API.
- Adds round-trip, tampering, wrong-key, wrong-key-type, wrong-password,
  permission, malformed-envelope, descriptor, schema, and CLI regression tests.

The signature proves possession of the private key corresponding to the
trusted public key. It proves a person's identity only when the public key or
fingerprint is authenticated independently. ReproCheck does not provide a
trusted timestamp, key revocation infrastructure, or long-term archival
validation.
