# Exercise 5 – ML Link Quality Baseline

## Classification Report (window_s = 5)

```text
              precision    recall  f1-score   support

stable           0.99      0.99      0.99       257
degraded         0.89      0.84      0.86        19

accuracy                              0.98       276
macro avg        0.94      0.92      0.93       276
weighted avg     0.98      0.98      0.98       276
```

## Early Warning Performance

* Failure injected at: t = 60 s
* First alert fired at: t = 57 s
* Early-warning lead time: 3.0 s

The classifier detected degradation before the simulated link failure, providing useful warning time.

## Feature Importances

| Feature       | Importance |
| ------------- | ---------- |
| hello_ratio   | 0.2215     |
| fwd_mean      | 0.4609     |
| fwd_std       | 0.1578     |
| n_miss_window | 0.1598     |

The most important feature was **fwd_mean**, indicating that forwarding-rate degradation is a strong
 indicator of impending link failure.

## Window Size Experiment

### window_s = 10

```text
              precision    recall  f1-score   support

stable           1.00      0.99      0.99       245
degraded         0.86      1.00      0.93        19

accuracy                             0.99       264
macro avg        0.93      0.99      0.96       264
 weighted avg    0.99      0.99      0.99       264
```

Feature importances:

* hello_ratio = 0.1878
* fwd_mean = 0.5333
* fwd_std = 0.1597
* n_miss_window = 0.1192

First alert fired at t = 37 s.

Early-warning lead time = 23.0 s.

### Comparison

| Metric              | 5 s Window | 10 s Window |
| ------------------- | ---------- | ----------- |
| Recall (degraded)   | 0.84       | 1.00        |
| F1 Score (degraded) | 0.86       | 0.93        |
| Lead Time           | 3.0 s      | 23.0 s      |

Increasing the window size improved degraded-link detection and substantially increased early-warning
 lead time. The larger window captured longer-term trends in HELLO reception and forwarding-rate degradation, making the model more sensitive to gradual failures.
