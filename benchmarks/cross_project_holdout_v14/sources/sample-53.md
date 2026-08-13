# Evaluation Report

## Objective
Evaluate trained pneumonia classifiers on the Chest X-Ray test split and summarize interpretability findings using Grad-CAM, with clinical emphasis on pneumonia recall (sensitivity).

## Data and Artifact Provenance
- Dataset source: KaggleHub `paultimothymooney/chest-xray-pneumonia`
- Resolved evaluation data directory:
  `C:\Users\aidan\.cache\kagglehub\datasets\paultimothymooney\chest-xray-pneumonia\versions\2\chest_xray`
- Test split size: 624 images (234 NORMAL, 390 PNEUMONIA)
- Checkpoints sourced from `origin/part-2` branch (`results/checkpoints/{model}_best.pt`)
- Evaluation script: `src/evaluate.py`
- Visualization/interpretability script: `src/interpret.py`
- Final notebooks:
  - `notebooks/02_evaluation.ipynb`
  - `notebooks/03_gradcam.ipynb`

## Quantitative Results

| Model | Accuracy | Pneumonia Recall (Sensitivity) | Pneumonia Precision | Pneumonia F1 | Normal Recall | Normal Precision | Macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `custom_cnn` | 0.8333 | 0.9128 | 0.8357 | 0.8725 | 0.7009 | 0.8283 | 0.8159 |
| `densenet121` | 0.8878 | 0.9897 | 0.8540 | 0.9169 | 0.7179 | 0.9767 | 0.8722 |

Reference files:
- `results/metrics/custom_cnn_metrics.json`
- `results/metrics/densenet121_metrics.json`

## Confusion Matrix Analysis

`custom_cnn` (test, 624 samples):
- TN = 164, FP = 70, FN = 34, TP = 356

`densenet121` (test, 624 samples):
- TN = 168, FP = 66, FN = 4, TP = 386

Interpretation:
- DenseNet121 dominates on every metric: higher accuracy, higher sensitivity, and meaningfully higher NORMAL precision.
- DenseNet121 misses only 4 pneumonia cases out of 390 (sensitivity 0.9897), making it suitable as a screening model where missed pneumonia cases are costly.
- Both models still confuse some NORMAL cases as PNEUMONIA (FP 70 and 66), so neither produces high specificity at the current threshold.
- For a clinical screening tool, DenseNet121's profile (high sensitivity with reasonable specificity) is the stronger candidate.

Reference figures:
- `results/confusion_matrices/custom_cnn_confusion_matrix.png`
- `results/confusion_matrices/densenet121_confusion_matrix.png`

## Training Trend Observations
Training history (CSV logs in `results/logs/`):
- `custom_cnn` reaches a best val loss of ~0.88 at epoch 1 and shows mild overfitting later in the 15-epoch run, with validation loss climbing while train loss continues to decrease.
- `densenet121` converges quickly with transfer learning, reaching best val loss ~0.086 (val_acc 0.9375) by epoch 6 in a 10-epoch run; training accuracy exceeds 0.99 by the end.
- DenseNet121's superior validation behavior carries over to the test set, consistent with the final per-class metrics.

Reference figures:
- `results/plots/custom_cnn_training_curves.png`
- `results/plots/densenet121_training_curves.png`
- `results/plots/model_comparison_validation_curves.png`

## Interpretability (Grad-CAM)
Grad-CAM overlays were generated for both models:
- `results/gradcam/custom_cnn_gradcam_000.png` ... `custom_cnn_gradcam_005.png`
- `results/gradcam/densenet121_gradcam_000.png` ... `densenet121_gradcam_005.png`

Interpretation notes:
- Both models attend primarily to the lung field rather than borders or backgrounds, which is a reasonable qualitative signal.
- DenseNet121 heatmaps tend to be more focal and aligned with opacities consistent with consolidation patterns; `custom_cnn` heatmaps are coarser and more diffuse.
- Heatmaps should still be paired with quantitative metrics rather than used standalone as clinical evidence.

## Limitations
- Single test snapshot: results reflect one held-out split from KaggleHub v2 of the dataset; generalization to other distributions is not assessed.
- No threshold sweep / calibration: confusion matrices use the default `argmax` decision; an operating-point analysis (ROC/PR curves) was not performed.
- Class imbalance present in training and test (more PNEUMONIA than NORMAL) is partially mitigated via class-weighted loss but not fully removed.
- Compute substrate is CPU for evaluation in the local environment; results are deterministic but slower than a GPU run would be.

## Final Conclusion
- Part 3 evaluation and interpretability pipelines are fully implemented and reproducible from `src/`.
- Final artifacts (metrics JSON, confusion matrices, training plots, Grad-CAM overlays, notebooks) are regenerated end-to-end from the verified `part-2` checkpoints.
- DenseNet121 is the recommended model for the project: 0.8878 accuracy, 0.9897 pneumonia sensitivity, and 0.9767 NORMAL precision, with only 4 missed pneumonia cases.
- The custom CNN is a useful lightweight baseline (0.8333 accuracy, 0.9128 sensitivity) but is dominated by DenseNet121 across all clinical-priority metrics.
