# Reproducibility guide

## Full verification

Use Python 3.11 or newer from a clean checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -c requirements-ci.txt -e '.[dev]'
make gate
```

The gate checks formatting, static types, 97% minimum coverage, controlled
defects, frozen public artifacts, mutation controls, every source/annotation
hash, external audit certificates, wheel replays, and package construction.

For a user project, keep `reprocheck.json` beside the paths it references and
run:

```bash
reprocheck check reprocheck.json --output-dir outputs/reprocheck
reprocheck verify --certificate outputs/reprocheck/batch-certificate.json --artifact-dir .
```

The first command creates independently verifiable child certificates and a
manifest-bound batch certificate. The second command rechecks certificate
schemas and digests, manifest provenance, nested artifact paths, byte sizes,
and source SHA-256 values without rerunning model code.

To authenticate the exact batch certificate bytes, sign them with a private
Ed25519 key and verify them against a public key obtained through a separate
trusted channel:

```bash
export REPROCHECK_KEY_PASSWORD='use-a-long-secret-from-your-password-manager'
reprocheck keygen --private-key reprocheck.private.pem --public-key reprocheck.public.pem
reprocheck sign --certificate outputs/reprocheck/batch-certificate.json \
  --private-key reprocheck.private.pem
reprocheck verify-signature \
  --certificate outputs/reprocheck/batch-certificate.json \
  --signature outputs/reprocheck/batch-certificate.json.sig.json \
  --public-key reprocheck.public.pem \
  --artifact-dir .
```

This is an authenticity check, not a trusted timestamp or proof that the
independently supplied identity-to-key binding is correct.

## Evidence phases

| Artifact | Scientific phase | Immutable command |
| --- | --- | --- |
| v0.5 challenge | zero-shot | `make challenge-replay` |
| v0.6 challenge | development after challenge inspection | `make challenge-replay` |
| v0.6 AP holdout | preregistered zero-shot | `make holdout-replay` |
| v0.7 AP holdout | development after v0.6 inspection | `make holdout-development` |
| v0.7 cross-domain holdout | preregistered zero-shot | `make holdout-v07` |
| v0.8 cross-domain result | development after v0.7 inspection | `make holdout-v08-development` |

Do not compare a development score with a zero-shot score as if both estimated
generalization. The repository intentionally preserves failures and label
problems instead of rewriting historical results.

## Deterministic package build

```bash
SOURCE_DATE_EPOCH=1704067200 python3 -m build
shasum -a 256 dist/*
```

Build hashes are release-specific. Frozen evaluator hashes are stored beside
their manifests and are verified by replay targets.
