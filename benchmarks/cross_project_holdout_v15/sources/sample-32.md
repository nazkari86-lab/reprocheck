# Raw-Data Reproducible Experiment Results

These results are recomputed by `reproduce_matbench_candidate.py` from public Matbench raw data. They are not the original Product descriptor-transfer values.

## Decision

- Status: `available_but_does_not_reproduce_product_scientific_claim`
- Product claim reproduced from raw data: `false`
- Discovery-score eligible: `false`
- Reproducible proxy residual R2 delta: `0.1022`

## Metrics

| Check | R2 | MAE | RMSE |
| --- | ---: | ---: | ---: |
| `null_or_trivial_rule` | -9.22803e-06 | 1.05871 | 1.35942 |
| `composition_formula_size` | 0.0612526 | 0.981016 | 1.31713 |
| `matched_negative_shuffled_target` | -0.0603866 | 1.09242 | 1.39986 |
| `candidate_formula_descriptor_proxy` | 0.163452 | 0.91398 | 1.24336 |

## Interpretation

The proxy experiment is exactly reproducible from public raw data and this script. It does not reproduce the Product descriptor-transfer scientific claim because the original descriptor matrix, model config, split manifest, target subset, residual formula, and baseline implementations were not present in Product artifacts.
