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
