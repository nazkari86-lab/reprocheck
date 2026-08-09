# YOLO26n / COCO8 external check

This bundle records an official Ultralytics 8.4.116 validation run and an
independent ReproCheck metric calculation over the exported boxes.

## Scope

- Model: official `yolo26n.pt`, SHA-256 recorded in `manifest.json`.
- Data: COCO8 validation split, 4 images and 17 ground-truth boxes.
- Runtime: CPU, image size 640, batch 4, confidence floor 0.001, NMS IoU 0.7.
- AP convention: Ultralytics-compatible 101-point trapezoidal integration.

COCO8 is a pipeline smoke test. These results must not be presented as
COCO val2017 model quality.

## Result

| Metric | Official | ReproCheck | Absolute difference |
| --- | ---: | ---: | ---: |
| mAP50-95 | 0.6647706555 | 0.6653767161 | 0.0006060606 |
| mAP50 | 0.9064941895 | 0.9064941895 | 0 |
| mAP75 | 0.8136868687 | 0.8136868687 | 0 |

The small mAP50-95 difference is caused by the three-decimal bbox and
five-decimal confidence rounding in the exported Ultralytics JSON. A second
official run reproduced all three official metrics exactly.

## Audit

```bash
reprocheck audit \
  --report benchmarks/external/yolo26n-coco8/report.md \
  --metrics benchmarks/external/yolo26n-coco8/official_metrics_flat.json \
  --detections benchmarks/external/yolo26n-coco8/coco8_detections.json \
  --tolerance 0.001 \
  --output outputs/yolo26n-coco8-audit.json \
  --html outputs/yolo26n-coco8-audit.html
```
