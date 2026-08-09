# ReproCheck

[![CI](https://github.com/nazkari86-lab/reprocheck/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/reprocheck/actions/workflows/ci.yml)
[![Python 3.11-3.14](https://img.shields.io/badge/python-3.11--3.14-3776ab.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

ReproCheck traces numerical claims in a research report to deterministic metric
calculations, notebook risks, and dataset-split evidence. It intentionally does
not execute uploaded Python or notebook code.

## What ReproCheck verifies

- Extracts classification, segmentation, and detection metric claims from
  Russian or English Markdown, TXT, DOCX, PDF, Jupyter, and JSON reports,
  including structured JSON metric names and Markdown/HTML result tables.
- Preserves scoped table metrics such as `box_ap`, `mask_ap`, `keypoint_ap`,
  `proposal_ar`, and `pq`, while rejecting ambiguous multi-number cells.
- Recomputes classification metrics from a `predictions.csv` file.
- Recomputes regression MAE, RMSE, and R² from numeric predictions, including
  valid negative R² values.
- Recomputes binary hard Dice and hard IoU from pixel/label predictions.
- Independently recomputes detection `mAP50`, `mAP75`, and `mAP50-95` from
  ground-truth and predicted bounding boxes.
- Supports binary, macro, and weighted multiclass averaging with an explicit
  positive label.
- Accepts precomputed evidence from `metrics.json`, long-form CSV, or a
  selected experiment row in a wide CSV table.
- Detects exact, normalized, group, and heuristic text overlap between train and
  test CSV files.
- Statically flags suspicious notebook execution order, preprocessing before a
  split, fitting on test-named data, and missing common seed declarations.
- Records artifact hashes, metric methods, confidence intervals, parameters,
  and an integrity checksum in a machine-readable report.
- Distinguishes a metric copied from supplied evidence (`supported`) from one
  independently recomputed from raw predictions (`verified`).
- Rejects conflicting evidence instead of silently choosing one source.
- Generates a standalone HTML report and provides a local web interface.

## Quick start

```bash
git clone https://github.com/nazkari86-lab/reprocheck.git
cd reprocheck
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -c requirements-ci.txt -e '.[dev]'
reprocheck demo
reprocheck check examples/reprocheck.json --output-dir outputs/project --html
reprocheck benchmark
reprocheck study --corpus benchmarks/real_artifacts
reprocheck serve
make gate
```

Open <http://127.0.0.1:8000> after starting the server.

## One-command project check

Store all experiment inputs in a versioned `reprocheck.json` manifest instead
of maintaining long shell commands:

```json
{
  "schema_version": "reprocheck.project.v1",
  "experiments": [
    {
      "id": "classifier",
      "report": "results/report.md",
      "predictions": "results/predictions.csv",
      "train": "data/train.csv",
      "test": "data/test.csv",
      "label_column": "label",
      "identity_columns": ["sample_id"]
    }
  ]
}
```

Run and verify the whole project:

```bash
reprocheck check reprocheck.json --output-dir outputs/reprocheck --html
reprocheck verify \
  --certificate outputs/reprocheck/batch-certificate.json \
  --artifact-dir .
```

Paths are resolved relative to the manifest and cannot escape that directory,
including through symlinks. The command validates the manifest before reading
evidence, audits every experiment, writes one normal certificate per experiment,
and then seals a batch certificate that binds the manifest and every child
certificate. Exit code `0` means all experiments passed, `1` means review is
required, and `2` means the input contract is invalid.

Use the same gate in GitHub Actions:

```yaml
- uses: actions/checkout@v7
- uses: nazkari86-lab/reprocheck@v0.10.0
  with:
    manifest: reprocheck.json
    output-dir: outputs/reprocheck
```

The action installs the tagged ReproCheck source, runs the project check, and
fails the job when any experiment needs review or the manifest is invalid.

## CLI audit

```bash
reprocheck audit \
  --report examples/report.md \
  --predictions examples/predictions.csv \
  --train examples/train.csv \
  --test examples/test.csv \
  --label-column label \
  --group-column source_id \
  --identity-columns text \
  --artifact model=models/model.bin \
  --artifact environment=requirements.lock \
  --output outputs/audit.json \
  --html outputs/audit.html
```

Verify that a saved certificate satisfies schema v1.2 and that its checksum and
source files have not changed:

```bash
reprocheck verify \
  --certificate outputs/audit.json \
  --artifact-dir examples
```

## Authenticated signatures

Generate an encrypted Ed25519 key once. The password is read from an
environment variable and is never accepted as a command-line argument:

```bash
export REPROCHECK_KEY_PASSWORD='use-a-long-secret-from-your-password-manager'
reprocheck keygen \
  --private-key reprocheck.private.pem \
  --public-key reprocheck.public.pem
reprocheck sign \
  --certificate outputs/reprocheck/batch-certificate.json \
  --private-key reprocheck.private.pem
```

Keep the private key out of Git. Publish the public key and its displayed
SHA-256 fingerprint through a separate trusted channel. A reviewer verifies
the certificate, all linked artifacts, the signature, and signer key together:

```bash
reprocheck verify-signature \
  --certificate outputs/reprocheck/batch-certificate.json \
  --signature outputs/reprocheck/batch-certificate.json.sig.json \
  --public-key reprocheck.public.pem \
  --artifact-dir .
```

This proves that the exact certificate bytes were signed by the private key
corresponding to the trusted public key. It proves an author's identity only
when that public key or fingerprint was authenticated independently, and it
does not provide a trusted timestamp.

## Input contracts

`predictions.csv`:

```csv
y_true,y_pred
cat,cat
dog,cat
```

`metrics.json`:

```json
{"accuracy": 0.91, "f1": 0.89}
```

The detection, project, and certificate contracts are published as JSON Schema:
[`detections-v1.schema.json`](src/reprocheck/schemas/detections-v1.schema.json)
and
[`project-manifest-v1.schema.json`](src/reprocheck/schemas/project-manifest-v1.schema.json),
[`audit-report-v1.2.schema.json`](src/reprocheck/schemas/audit-report-v1.2.schema.json),
and
[`batch-certificate-v1.schema.json`](src/reprocheck/schemas/batch-certificate-v1.schema.json).
Detached signatures follow
[`certificate-signature-v1.schema.json`](src/reprocheck/schemas/certificate-signature-v1.schema.json).
The frozen public-corpus result follows
[`real-study-v2.schema.json`](src/reprocheck/schemas/real-study-v2.schema.json).
The cross-repository challenge outputs follow
[`challenge-study-v1.schema.json`](src/reprocheck/schemas/challenge-study-v1.schema.json)
and
[`challenge-study-v2.schema.json`](src/reprocheck/schemas/challenge-study-v2.schema.json).

Use the parser directly when an audit certificate is not needed:

```python
from reprocheck import extract_claims, extract_table_claims

all_claims = extract_claims(report_text)
table_claims = extract_table_claims(report_text)
```

Select an exact claim and experiment from a research repository:

```bash
reprocheck audit \
  --report benchmarks/v2/claims_registry.json \
  --report-selector claims.0.claim \
  --metrics benchmarks/v2/tables/metrics_summary.csv \
  --metrics-selector experiment=compact_ablation_sentinel1_2017_2024
```

Train and test files must have headers. By default, all common columns except
the label column form a row identity. `--group-column` additionally checks that
one patient, user, source, or event does not occur in both splits.

## Current scientific boundary

An audit can prove exact overlap relative to the uploaded files and declared
columns. It cannot prove that all semantic near-duplicates or every possible
methodological error have been found. A reproduced number can still support a
bad hypothesis; ReproCheck reports computational evidence, not scientific
truth.

The exact guarantee and proposed evaluation protocol are documented in
[`docs/SCIENTIFIC_PROTOCOL.md`](docs/SCIENTIFIC_PROTOCOL.md). Upload safety is
documented in [`SECURITY.md`](SECURITY.md). The component boundary is described
in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Version 0.6 changes are
summarized in [`docs/RELEASE_0.6.md`](docs/RELEASE_0.6.md); the narrow post-holdout
0.7 and 0.8 corrections are documented in
[`docs/RELEASE_0.7.md`](docs/RELEASE_0.7.md) and
[`docs/RELEASE_0.8.md`](docs/RELEASE_0.8.md). Publication metadata changes are
listed in [`docs/RELEASE_0.8.1.md`](docs/RELEASE_0.8.1.md) and
[`docs/RELEASE_0.8.2.md`](docs/RELEASE_0.8.2.md) through
[`docs/RELEASE_0.8.4.md`](docs/RELEASE_0.8.4.md). The manifest-driven project
check is documented in [`docs/RELEASE_0.9.md`](docs/RELEASE_0.9.md). The
authenticated-signature layer is documented in
[`docs/RELEASE_0.10.md`](docs/RELEASE_0.10.md), and all immutable commands are
indexed in [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## Frozen real-artifact evidence

The original study includes an exhaustive-within-declared-paths corpus of 60
complete files from pinned MONAI Model Zoo, Hugging Face Transformers, and
TensorFlow Docs commits. ReproCheck 0.5 recovered all 40 annotated supported
claims with 40 TP, 0 FP, and 0 FN. Version 0.6 preserves the same result. The
Wilson 95% lower bound for both precision and recall is 91.24%; 100% is the
observed sample result, not a universal guarantee.

A deliberately simple inline-regex baseline recovered 8/40 claims (20.0%). The
paired mean per-artifact recall improvement was 72.92 percentage points, with a
deterministic paired-bootstrap 95% interval of 56.25 to 87.50 points. A stronger
format-aware baseline with explicit `eval_metrics` and Markdown-table knowledge
also recovered 40/40, so ReproCheck ties rather than beats it on this corpus.

The expanded mutation matrix contains 67 real-file defects and 63 negative
controls. ReproCheck and the format-aware baseline both detected 67/67 defects
and preserved 63/63 equivalent controls. The naive regex detected 8/67 defects
and correctly preserved only 12/63 controls because it omitted most structured
claims. ReproCheck also matched the stored internal risk labels for 7/7 notebooks.

These labels are not independent expert ground truth: 30 claims are derived
from explicit MONAI `eval_metrics` fields, 10 claims have one internal reviewer,
and the notebook labels have one internal reviewer. There are currently zero
independent external annotators and no adjudication. Run the exact frozen study
from a source checkout with `make study`; its corpus hashes, raw result, baseline,
and limitations are under [`benchmarks/real_artifacts`](benchmarks/real_artifacts).

## Cross-repository format challenge

A second corpus was selected only after the 0.5 wheel was frozen and before its
zero-shot evaluation: Detectron2 `MODEL_ZOO.md` plus all 113 MMDetection
`configs/*/README.md` files at pinned commits. It contains 114 artifacts and
1,006 rule-derived AP/AR/PQ table claims. The frozen 0.5 wheel recovered only
18/1,006 claims (1.79% recall; Wilson 95% 1.13%-2.81%), exposing a real format
coverage failure rather than another favorable benchmark.

After that result was inspected, version 0.6 added general Markdown/HTML table
support and recovered 1,006/1,006 frozen labels with 2 strict false positives:
99.80% precision (Wilson 95% 99.28%-99.95%) and 100% recall (Wilson 95%
99.62%-100%). Both extras are valid spelled-out `Average Precision` cells that
the frozen annotation rule omitted; this post-hoc review is recorded separately
and is not used to alter the primary score.

The 0.6 challenge number is a development-set result, not independent evidence
of generalization, because the parser was improved after examining that corpus.
Run `make challenge` for source/result checks and `make challenge-replay` for
byte-identical replay from both stored wheels.

## Preregistered zero-shot holdout

A separate v0.6 holdout was preregistered before downloading file contents and
before running the frozen evaluator. It contains 25 complete files and 313
in-scope AP-family claims from pinned Ultralytics, YOLOv5, DETR, and YOLOX
repositories. The immutable zero-shot result is 297 TP, 67 FP, and 16 FN:
81.59% precision (Wilson 95% 77.29%-85.24%) and 94.89% recall (Wilson 95%
91.86%-96.83%). Twenty-three of 25 files were exact.

Post-hoc review, excluded from primary scoring, identified a frozen metric-label
error responsible for 16 FP plus 16 FN and genuine evaluator over-extraction of
51 size-specific AP cells. This is materially stronger than reporting only the
adapted challenge score, but still uses one internal annotation reviewer and a
computer-vision-heavy corpus. Run `make holdout` for immutable checks and
`make holdout-replay` for a byte-identical clean-wheel replay.

Version 0.7 removes the 51 confirmed size-specific AP over-extractions on this
already-inspected holdout. Against corrected post-hoc metric categories it
produces 313 TP, 0 FP, and 0 FN, but this is explicitly development evidence,
not a second zero-shot score. A new unseen holdout is required to test v0.7.

## Cross-domain v0.7 zero-shot evidence

That new holdout was preregistered against the frozen v0.7 wheel before source
contents were downloaded. Hash-ranked sampling selected 39 complete files from
timm, MMSegmentation, fairseq, and PaddleClas, with 295 independently generated
table labels. Version 0.7 achieved 259 TP, 0 FP, and 36 FN: 100% observed
precision (Wilson 95% 98.54%-100%) and 87.80% recall (Wilson 95%
83.57%-91.05%). It recovered mIoU 249/249 and Accuracy 4/4, but only 6/42
standalone Top-1/Top-5 claims.

All misses are explained by one unseen header gap: v0.7 requires an `accuracy`
token next to Top-1/Top-5. The primary score, preregistration, labels, and result
are immutable and byte-identically replayed by `make holdout-v07`. This broader
holdout remains internally annotated and mIoU-heavy; it is evidence on the
declared corpus, not a universal accuracy claim.

Version 0.8 fixes this discovered Top-K boundary and recovers 295/295 labels
with no extras on the already-inspected corpus. That result is explicitly
post-holdout development evidence. It demonstrates correction of the observed
failure, while the frozen v0.7 zero-shot score remains the generalization
measurement.

External evidence includes YOLO26n/COCO8 detection plus scikit-learn Iris
classification and Diabetes regression. Their raw prediction evidence,
independent reference metrics, split IDs, and manifests are stored under
[`benchmarks/external`](benchmarks/external).
