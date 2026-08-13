# Business Report

RevenueGuard AI highlights shifts with statistically unusual revenue patterns. It does not claim theft.

## Model Performance
```text
            model         mae        rmse       r2                                                                       best_params
          xgboost  895.903534 1191.938351 0.922278 {'model__learning_rate': 0.03, 'model__max_depth': 3, 'model__n_estimators': 150}
    random_forest  969.982331 1276.857535 0.910810                               {'model__max_depth': 5, 'model__n_estimators': 300}
linear_regression 1407.079018 1585.318716 0.862511                                                                                {}
```

## Top Investigation Queue
| Date | Pair | Actual | Expected | Deviation | Risk | Why Review |
|---|---|---:|---:|---:|---:|---|
| 2025-09-30 | Бедняков + Воронов | 16320 | 18543 | -2223 | 66.4 | actual revenue is below model-expected revenue |
| 2025-09-29 | Воронов + Гранин | 16490 | 18745 | -2255 | 64.3 | actual revenue is below model-expected revenue |
| 2025-09-26 | Воронов + Гранин | 15810 | 17401 | -1591 | 50.7 | actual revenue is below model-expected revenue |
| 2025-09-17 | Воронов + Гранин | 16660 | 18346 | -1686 | 49.9 | actual revenue is below model-expected revenue |
| 2025-09-24 | Алексеев + Бедняков | 18600 | 20761 | -2161 | 46.1 | actual revenue is below model-expected revenue |
| 2025-08-03 | Бедняков + Воронов | 6525 | 7130 | -605 | 39.4 | actual revenue is below model-expected revenue; weekend context is included in the comparison |
| 2025-08-04 | Алексеев + Бедняков | 21400 | 20840 | 560 | 37.5 | multiple unsupervised detectors agree on high anomaly intensity |
| 2025-09-20 | Бедняков + Воронов | 9895 | 10664 | -769 | 34.9 | actual revenue is below model-expected revenue; weekend context is included in the comparison |
| 2025-08-17 | Алексеев + Воронов | 6735 | 7145 | -410 | 33.1 | revenue is materially below the recent distribution; actual revenue is below model-expected revenue; weekend context is included in the comparison |
| 2025-09-11 | Воронов + Гранин | 16490 | 17151 | -661 | 32.8 | actual revenue is below model-expected revenue |

## Recommended Controls
- Reconcile cash, POS orders, refunds, discounts, and voids for high-risk shifts.
- Add footfall, building occupancy, weather, menu mix, and promotion data before making policy decisions.
- Use rotating controls and audit procedures consistently across employees.