# ADV Kernel — Adaptive Density Variance Kernel

[![CI](https://github.com/InquietoPartho/adv_kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/InquietoPartho/adv_kernel/actions)
[![PyPI](https://img.shields.io/pypi/v/adv-kernel)](https://pypi.org/project/adv-kernel/)
[![Python](https://img.shields.io/pypi/pyversions/adv-kernel)](https://pypi.org/project/adv-kernel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A scikit-learn compatible **SVM kernel** that adapts its bandwidth sample-by-sample using two complementary signals:

| Signal | Meaning |
|---|---|
| **k-NN density** | Sparse neighbourhood → wider kernel |
| **Feature variance** | High intra-sample heterogeneity → wider kernel |

The final kernel is a **pointwise product** of an adaptive RBF and a polynomial term:

```
K(xᵢ, xⱼ) = exp(−‖xᵢ−xⱼ‖² / 2σᵢσⱼ) × (1 + β⟨xᵢ,xⱼ⟩)^degree
```

---

## Installation

```bash
pip install adv-kernel
```

Or directly from GitHub:

```bash
pip install git+https://github.com/InquietoPartho/adv_kernel.git
```

---

## Quick start

```python
from adv_kernel import ADVKernelSVC

clf = ADVKernelSVC(C=1.0, beta=0.5, degree=2, probability=True)
clf.fit(X_train, y_train)

y_pred  = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)
```

### Use kernel functions directly

```python
from adv_kernel import adv_bandwidth, adv_kernel

sigma = adv_bandwidth(X, k=10, gamma_density=1.0, gamma_var=0.5)
K     = adv_kernel(X, X, sigma, sigma, beta=0.5, degree=2)
```

### scikit-learn GridSearchCV

```python
from sklearn.model_selection import GridSearchCV
from adv_kernel import ADVKernelSVC

param_grid = {"C": [0.1, 1.0, 10.0], "beta": [0.2, 0.5], "gamma_density": [0.5, 1.0]}
gs = GridSearchCV(ADVKernelSVC(), param_grid, cv=5, n_jobs=-1)
gs.fit(X_train, y_train)
print(gs.best_params_)
```

---

## API reference

### `adv_bandwidth(X, k=10, gamma_density=1.0, gamma_var=0.5)`
Returns per-sample bandwidth array of shape `(n_samples,)`.

### `adv_kernel(X, Y, sigma_X, sigma_Y, beta=0.5, degree=2)`
Returns kernel matrix of shape `(n_X, n_Y)`.

### `ADVKernelSVC` parameters

| Parameter | Default | Description |
|---|---|---|
| `C` | `1.0` | SVM regularisation |
| `beta` | `0.5` | Polynomial scaling |
| `degree` | `2` | Polynomial degree |
| `k_bw` | `10` | k-NN neighbours for bandwidth |
| `gamma_density` | `1.0` | Density term weight |
| `gamma_var` | `0.5` | Variance term weight |
| `probability` | `True` | Enable `predict_proba` |

---

## Data Preprocessing & Benchmark Pipeline

The following pseudocode describes the full experimental pipeline used in the paper, including data preprocessing, repeated stratified cross-validation, and statistical testing.

```
ALGORITHM: ADV Kernel Benchmark Pipeline
─────────────────────────────────────────────────────────────────────
INPUT  : Dataset D = {(xᵢ, yᵢ)}ᵢ₌₁ᴺ
         Models  M = {Linear SVM, RBF SVM, Poly SVM, Sigmoid SVM, ADV}
         N_SPLITS = 5, N_REPEATS = 5

─────────────────────────────────────────────────────────────────────
STEP 1 — DATA LOADING
─────────────────────────────────────────────────────────────────────
  Load dataset from CSV (e.g., heart.csv)
  Separate features X and target y
  Verify class distribution (check for imbalance)
  Confirm no missing values

─────────────────────────────────────────────────────────────────────
STEP 2 — REPEATED STRATIFIED CROSS-VALIDATION
─────────────────────────────────────────────────────────────────────
  FOR rep = 1 to N_REPEATS:
    skf ← StratifiedKFold(n_splits=N_SPLITS,
                          shuffle=True,
                          random_state=42 + rep)

    FOR each (train_idx, test_idx) in skf.split(X, y):

      // --- Preprocessing (inside fold — no leakage) ---
      X_train, X_test ← X[train_idx], X[test_idx]
      y_train, y_test ← y[train_idx], y[test_idx]

      scaler ← StandardScaler()
      X_train ← scaler.fit_transform(X_train)   // fit on train only
      X_test  ← scaler.transform(X_test)        // apply to test

      // --- Train & Evaluate each model ---
      FOR each model m in M:
        m.fit(X_train, y_train)
        y_pred ← m.predict(X_test)
        y_prob ← m.predict_proba(X_test)[:, 1]

        // --- Compute metrics ---
        report  ← classification_report(y_test, y_pred)
        fpr, tpr ← roc_curve(y_test, y_prob)

        STORE accuracy, precision, recall, F1, ROC-AUC
      END FOR
    END FOR
  END FOR

─────────────────────────────────────────────────────────────────────
STEP 3 — AGGREGATE RESULTS
─────────────────────────────────────────────────────────────────────
  FOR each model m in M:
    Compute mean ± std over all (N_SPLITS × N_REPEATS) folds
    Report: Accuracy, Precision, Recall, F1-score, ROC-AUC
  END FOR
  Save results to CSV

─────────────────────────────────────────────────────────────────────
STEP 4 — STATISTICAL TESTING
─────────────────────────────────────────────────────────────────────
  // Pairwise test: ADV vs RBF SVM
  stat, p ← Wilcoxon signed-rank test(
                F1_scores[ADV], F1_scores[RBF],
                alternative='two-sided')

  // Global test: all models simultaneously
  stat, p ← Friedman test(F1_scores[m] for all m in M)

  Report p-values and significance (threshold α = 0.05)

OUTPUT : Mean ± Std results table, statistical test results, CSV
─────────────────────────────────────────────────────────────────────
```

> **Key preprocessing rule:** `StandardScaler` is always fitted on the training fold only (`fit_transform`) and applied to the test fold (`transform`). This prevents data leakage and ensures that test-set statistics do not influence the normalisation parameters.

---

## License

MIT © Pijush Kanti Roy Partho
