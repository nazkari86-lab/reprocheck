# Contributing

ReproCheck treats scientific evidence as an immutable artifact, not a benchmark
number that may be silently refreshed.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
make lint
make coverage
```

Before submitting a behavior change, run `make gate`. Parser changes informed
by a frozen holdout must use a new package version. Never overwrite a primary
zero-shot result, annotation lock, source manifest, evaluator wheel, or its
SHA-256 binding. Store post-hoc reviews and adapted results separately and mark
them as development evidence.

## Pull requests

- Explain the behavioral boundary being changed and add positive and negative
  regression tests.
- State which frozen studies are expected to remain byte-identical.
- Update a deterministic baseline only for an intentional reviewed change.
- Do not add private, licensed-without-redistribution, or secret-bearing data.
- Keep generated outputs out of Git unless they are immutable study evidence.

Security reports should follow [SECURITY.md](SECURITY.md), not a public issue.
