# scikit-learn tabular external checks

This bundle independently exercises ReproCheck on two classic public datasets
shipped by scikit-learn 1.8.0. It covers multiclass classification, numeric
regression, metric-table selection, prediction recomputation, and split
identity checks.

## Frozen experiments

| Case | Samples | Split | Model |
| --- | ---: | --- | --- |
| Iris | 150 | stratified 70/30, seed 2026 | StandardScaler + LogisticRegression |
| Diabetes | 442 | 75/25, seed 2026 | StandardScaler + Ridge |

The repository does not copy the feature matrices. `generate.py` loads them
from `sklearn.datasets`; `manifest.json` records canonical data and target
SHA-256 values. The committed CSV files contain source-row IDs, targets, and
predictions needed for the audit.

## Results

| Case | Metric | scikit-learn | ReproCheck | Absolute difference |
| --- | --- | ---: | ---: | ---: |
| Iris | Accuracy | 0.9333333333333333 | 0.9333333333333333 | 0 |
| Iris | Macro precision | 0.9444444444444445 | 0.9444444444444444 | 1.11e-16 |
| Iris | Macro recall | 0.9333333333333332 | 0.9333333333333333 | 1.11e-16 |
| Iris | Macro F1 | 0.9326599326599326 | 0.9326599326599325 | 1.11e-16 |
| Diabetes | MAE | 42.858521361464824 | 42.85852136146482 | 7.11e-15 |
| Diabetes | RMSE | 54.244807679520214 | 54.24480767952021 | 7.11e-15 |
| Diabetes | R² | 0.5193247449368283 | 0.5193247449368285 | 1.11e-16 |

Both audits pass with tolerance `1e-9`. Exact and normalized train/test sample
ID overlap are zero in both cases.

## Reproduce

```bash
python3 -m pip install -e '.[benchmark]'
python3 benchmarks/external/sklearn-tabular/generate.py

reprocheck audit \
  --report benchmarks/external/sklearn-tabular/iris_report.md \
  --metrics benchmarks/external/sklearn-tabular/official_metrics.json \
  --metrics-selector iris \
  --predictions benchmarks/external/sklearn-tabular/iris_predictions.csv \
  --average macro \
  --train benchmarks/external/sklearn-tabular/iris_train.csv \
  --test benchmarks/external/sklearn-tabular/iris_test.csv \
  --label-column target \
  --identity-columns sample_id \
  --tolerance 1e-9 \
  --output outputs/iris-audit.json

reprocheck audit \
  --report benchmarks/external/sklearn-tabular/diabetes_report.md \
  --metrics benchmarks/external/sklearn-tabular/official_metrics.json \
  --metrics-selector diabetes \
  --predictions benchmarks/external/sklearn-tabular/diabetes_predictions.csv \
  --prediction-task regression \
  --train benchmarks/external/sklearn-tabular/diabetes_train.csv \
  --test benchmarks/external/sklearn-tabular/diabetes_test.csv \
  --label-column target \
  --identity-columns sample_id \
  --tolerance 1e-9 \
  --output outputs/diabetes-audit.json
```

These are compact pipeline checks, not estimates of state-of-the-art model
quality or evidence of clinical utility.
