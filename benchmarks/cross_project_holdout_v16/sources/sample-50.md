# DR Lesion Detection Evaluation Framework

A comprehensive, modular Python framework for evaluating trained YOLO models for Diabetic Retinopathy (DR) lesion detection. Designed for academic thesis work with publication-ready visualizations and rigorous metric calculations.

> This is the **evaluation/inference module** of the [PRISM-DR](../README.md) project. For the full training pipeline, method description, datasets, and results, see the repository root.

## Features

- **5-Fold Cross-Validation Evaluation**: Per-fold and aggregated metrics (mean ± std)
- **SAHI Integration**: Slicing Aided Hyper Inference for small lesion detection (MA, HE, EX)
- **Standard YOLO Inference**: For larger lesions (SE)
- **Cross-Fold Ensemble**: NMS/WBF fusion across all 5 models
- **GPU-Accurate Latency Profiling**: Warmup passes + CUDA synchronization
- **Publication-Ready Visualizations**: High-DPI figures for academic papers
- **Inter-Lesion Confusion Analysis**: MA vs HE cross-detection rates
- **Per-Lesion Configuration**: YAML-based parameter tuning

## Directory Structure

```
evaluation/
├── main.py                    # Main CLI entry point
├── confusion_analysis.py      # Inter-lesion confusion analysis
├── requirements.txt           # Python dependencies
├── configs/
│   └── inference.yaml         # Per-lesion configuration file
└── src/
    ├── __init__.py
    ├── config.py              # Configuration management
    ├── unified_boxes.py       # Unified bounding box adapter
    ├── metrics.py             # Detection metrics calculation
    ├── inference.py           # SAHI/YOLO inference engines
    └── visualize.py           # Publication-ready visualizations
```

## Installation

```bash
# From the repository root, install dependencies
pip install -r requirements.txt

# Then run the evaluation CLI from this directory
cd evaluation
```

### Requirements

- Python 3.8+
- PyTorch 2.0+
- CUDA 11.x+ (for GPU inference)

## Quick Start

### 1. Basic Evaluation (5-Fold CV)

```bash
# Evaluate a single lesion type
python main.py --lesion MA --device cuda

# Evaluate all lesion types sequentially
python main.py --lesion all --device cuda
```

### 2. Image-Level SAHI Evaluation

The `--image-level` flag runs evaluation on **original IDRiD images** using the same methodology that produced the published results. This differs from tile-level evaluation by:
- Loading original images (not pre-tiled)
- Applying ROI crop + CLAHE preprocessing
- Running SAHI inference on the full preprocessed image
- Getting ground truth from segmentation masks

```bash
# Validation mode: computes best_conf from F1-confidence curve
python main.py --lesion MA --image-level --device cuda

# Test mode: uses validation-derived confidence from config
# (avoids data leakage by using conf determined from validation set)
python main.py --lesion MA --image-level --test --device cuda

# Evaluate all lesions (fills val_best_conf values in config)
python main.py --lesion all --image-level --device cuda
```

The `val_best_conf` values in `configs/inference.yaml` are automatically used when `--test` is combined with `--image-level`.

### 3. Ensemble Inference

```bash
# Cross-fold ensemble with WBF/NMS merging
python main.py --lesion MA --ensemble --device cuda
```

### 4. Test Set Evaluation (IDRiD 27 Images)

The framework supports evaluation on both:
- **5-Fold CV Validation Splits**: Uses validation images from each fold's split of training data
- **Held-out Test Set**: Uses the IDRiD test set (27 images: IDRiD_55 to IDRiD_81)

```bash
# Evaluate all 5 folds on test set (reports per-fold + aggregated metrics)
python main.py --lesion MA --test --device cuda

# Test set with ensemble (combines all 5 folds using WBF/NMS)
python main.py --lesion MA --test --ensemble --device cuda

# Evaluate all lesions on test set
python main.py --lesion all --test --device cuda
```

### 5. Inter-Lesion Confusion Analysis

```bash
# Check how many HE lesions the MA model detects
python confusion_analysis.py --pred-lesion MA --gt-lesion HE --device cuda

# Bidirectional analysis (both directions)
python confusion_analysis.py --pred-lesion MA --gt-lesion HE --bidirectional
```

## Configuration

The `configs/inference.yaml` file allows per-lesion parameter tuning:

```yaml
lesions:
  MA:
    inference_mode: "sahi"      # sahi or standard
    tile_size: 1280
    overlap_ratio: 0.25
    conf_threshold: 0.001
    iou_threshold: 0.5
    match_iou: 0.5
    ensemble_method: "nms"      # nms or wbf
    skip_box_thr: 0.01
```

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `inference_mode` | `sahi` for tiled inference, `standard` for full-image | Per lesion |
| `tile_size` | Tile size for SAHI inference | 1280 |
| `overlap_ratio` | Overlap between tiles | 0.25 |
| `conf_threshold` | Confidence threshold for predictions | 0.001 |
| `iou_threshold` | IoU threshold for NMS/WBF | 0.5 |
| `match_iou` | IoU threshold for TP/FP matching | 0.5 |
| `ensemble_method` | `nms` or `wbf` for ensemble | nms |

## Output Structure

```
outputs/
├── MA_20240215_143022/
│   ├── metrics/
│   │   ├── fold_0_metrics.json
│   │   ├── fold_1_metrics.json
│   │   ├── fold_2_metrics.json
│   │   ├── fold_3_metrics.json
│   │   ├── fold_4_metrics.json
│   │   ├── per_fold_metrics.csv
│   │   ├── aggregated_metrics.csv
│   │   └── latency_stats.json
│   ├── visualizations/
│   │   ├── confusion_matrix.png
│   │   ├── f1_confidence_curve.png
│   │   ├── pr_curve.png
│   │   └── predictions/
│   │       ├── image_001_predictions.png
│   │       └── ...
│   └── config_used.yaml
```

## CLI Reference

### main.py

```
usage: main.py [-h] --lesion {MA,HE,EX,SE,all} [--device {cuda,cpu}]
               [--config CONFIG] [--output OUTPUT] [--ensemble]
               [--test] [--image-level] [--no-visualize] [--match-iou MATCH_IOU]

Arguments:
  --lesion        Lesion type to evaluate (MA, HE, EX, SE, or 'all')
  --device        Device for inference (cuda/cpu)
  --config        Path to custom configuration YAML
  --output        Base output directory (default: outputs)
  --ensemble      Run cross-fold ensemble instead of per-fold evaluation
  --test          Evaluate on IDRiD test set (27 images) instead of CV splits
  --image-level   Run image-level SAHI evaluation on original images
                  (matches original methodology; use with --test for test set)
  --no-visualize  Disable visualization generation
  --match-iou     Override IoU threshold for TP/FP classification
```

### confusion_analysis.py

```
usage: confusion_analysis.py [-h] --pred-lesion {MA,HE,EX,SE}
                              --gt-lesion {MA,HE,EX,SE}
                              [--device {cuda,cpu}] [--config CONFIG]
                              [--output OUTPUT] [--fold FOLD] [--bidirectional]

Arguments:
  --pred-lesion    Lesion type for predictions (model to use)
  --gt-lesion      Lesion type for ground truths
  --device         Device for inference
  --fold           Which fold to use (default: 1)
  --bidirectional  Run analysis in both directions
```

## Metrics Explained

### Preserved Metric Calculation

The framework preserves the exact metric calculation logic from the original evaluation code to ensure numerical consistency:

- **IoU Calculation**: Standard intersection-over-union
- **TP/FP/FN Matching**: Greedy matching sorted by confidence
- **Average Precision**: COCO-style 101-point interpolation
- **mAP@50:95**: Mean AP over IoU thresholds 0.5:0.05:0.95

### Output Metrics

| Metric | Description |
|--------|-------------|
| Precision | TP / (TP + FP) |
| Recall | TP / (TP + FN) |
| F1 | 2 × (P × R) / (P + R) |
| mAP@50 | Average Precision at IoU=0.5 |
| mAP@50:95 | Mean AP over IoU 0.5:0.05:0.95 |
| best_conf | Confidence threshold that maximizes F1 |

## Model Information

| Lesion | Model | Inference Mode | Description |
|--------|-------|----------------|-------------|
| MA | YOLOv5nu (P2) | SAHI | Microaneurysms (small, numerous) |
| HE | YOLO12n | SAHI | Hemorrhages (various sizes) |
| EX | YOLOv5nu | SAHI | Hard Exudates (small to medium) |
| SE | YOLO26n | Standard | Soft Exudates (larger, fewer) |

## Visualization Examples

### TP/FP/FN Prediction Image
- **Green boxes**: True Positives (correct detections)
- **Red boxes**: False Positives (incorrect detections)
- **Blue dashed boxes**: False Negatives (missed ground truths)

### F1-Confidence Curve
Shows F1 score vs confidence threshold with best operating point marked.

### Precision-Recall Curve
Shows P-R trade-off with area under curve (AP) displayed.

## Advanced Usage

### Custom Configuration

Create a custom YAML file modifying only the parameters you need:

```yaml
lesions:
  MA:
    conf_threshold: 0.1
    ensemble_method: "wbf"
```

Then run:
```bash
python main.py --lesion MA --config configs/custom.yaml
```

### Programmatic API

```python
from src import load_config, create_inference_engine, create_visualizer
from src.metrics import compute_all_metrics, find_best_f1_confidence

# Load configuration
config = load_config("configs/inference.yaml")

# Create inference engine
engine = create_inference_engine(config_path="configs/inference.yaml", device="cuda")

# Run evaluation
predictions, latency = engine.evaluate_fold("MA", fold=1)

# Compute metrics
all_preds = {img_id: ip.predictions for img_id, ip in predictions.items()}
all_gts = {img_id: ip.ground_truths for img_id, ip in predictions.items()}

best_conf, best_f1 = find_best_f1_confidence(all_preds, all_gts, iou_threshold=0.5)
metrics = compute_all_metrics(all_preds, all_gts, best_conf, match_iou=0.5)

print(f"F1: {metrics.f1:.4f}, mAP@50: {metrics.mAP50:.4f}")
```

## Troubleshooting

### CUDA Out of Memory
- Models are evaluated sequentially (not in parallel) to prevent OOM
- Reduce batch size or use CPU if still encountering issues

### Slow SAHI Inference
- SAHI is inherently slower due to tiled inference
- Consider reducing tile overlap or using standard inference for testing

### Missing Ground Truths
- Ensure YOLO TXT label files exist in the dataset's `labels/val/` directory
- Labels follow YOLO format: `class_id x_center y_center width height`

## Citation

If you use this framework in your research, please cite:

See [`CITATION.cff`](../CITATION.cff) in the repository root for citation details.

## License

MIT License — see [`LICENSE`](../LICENSE) and [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) in the repository root. Note that this framework uses Ultralytics YOLO (AGPL-3.0); review the third-party notices before redistribution or commercial use.
