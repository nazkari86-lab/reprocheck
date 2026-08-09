# Frozen real-artifact corpus

This corpus evaluates ReproCheck on complete files from three official public
repositories at immutable commits. Selection is exhaustive inside each declared
path pattern rather than based on whether ReproCheck succeeds:

- all 35 MONAI Model Zoo `models/*/configs/metadata.json` files;
- all 18 Hugging Face Transformers `examples/pytorch/**/README.md` files;
- all 7 TensorFlow Docs `site/en/tutorials/keras/*.ipynb` notebooks.

The 60 artifacts cover JSON model cards, Markdown experiment documentation,
and real notebooks. Every source URL, commit, byte size, SHA-256, and repository
license is recorded in `source_manifest.json`.

```bash
python3 benchmarks/real_artifacts/fetch_sources.py --fetch
python3 benchmarks/real_artifacts/fetch_sources.py
python3 benchmarks/real_artifacts/build_annotations.py
reprocheck study --corpus benchmarks/real_artifacts
python3 benchmarks/real_artifacts/check_baseline.py --result outputs/real-study.json
```

`fetch_sources.py --fetch` is the only networked step and is used only when
intentionally refreshing pinned sources. Without `--fetch`, it fails closed on
missing, extra, size-mismatched, or SHA-mismatched files. Likewise,
`build_annotations.py` checks the reviewed file by default; `--write` is an
explicit regeneration operation that must be reviewed before updating the
baseline.

The frozen copies make CI independent of GitHub availability. They remain
third-party files under their original Apache-2.0 licenses; see each vendored
repository `LICENSE` file. Benchmark annotations explicitly record whether
their labels are rule-derived, internally reviewed, or independently reviewed.
No internal label is described as external expert ground truth.

The deterministic v3 baseline excludes latency because it depends on hardware
and runtime load. It includes corpus hashes, repository commits, Wilson
intervals, paired-bootstrap results (5,000 samples, seed 2026), source-wise
summaries, two extraction baselines, and a 130-case mutation/control matrix.
`outputs/real-study.json` retains per-file latency and case records for local
inspection.
