# GPT-5.4 Reproduction Results

This page reports complete GPT-5.4 runs. Values are percentages rounded to two decimals. Main metrics follow [Evaluation Metrics](evaluation_metric_profiles.md); supplementary metrics are reported when available but are not the primary benchmark result for every dataset. 
All reported runs use GPT-5.4 xhigh for captioning; the low/xhigh variant shown in the tables refers to the reasoning/matching model setting.

## Complete Runs

| Dataset | Split | Captioning model | Reasoning model | Samples | No-target samples | Main metric(s) |
| --- | --- | --- | --- | ---: | ---: | --- |
| D-Cube | full | GPT-5.4 xhigh | GPT-5.4 xhigh | 42,102 | 29,067 (69.04%) | mAP Full/Pres/Abs: `41.19` / `41.78` / `39.33` |
| GRefCOCO | testB | GPT-5.4 xhigh | GPT-5.4 low | 14,933 | 4,242 (28.41%) | Pr. `57.93`, N-acc. `60.33` |
| GRefCOCO | testB | GPT-5.4 xhigh | GPT-5.4 xhigh | 14,933 | 4,242 (28.41%) | Pr. `59.18`, N-acc. `52.64` |
| RefCOCO+ | testA | GPT-5.4 xhigh | GPT-5.4 low | 5,726 | 0 (0.00%) | IoU@0.5 Accuracy `77.63` |
| RefCOCO+ | testA | GPT-5.4 xhigh | GPT-5.4 xhigh | 5,726 | 0 (0.00%) | IoU@0.5 Accuracy `79.17` |
| RefCOCO+ | testB | GPT-5.4 xhigh | GPT-5.4 low | 4,889 | 0 (0.00%) | IoU@0.5 Accuracy `70.24` |
| RefCOCO+ | testB | GPT-5.4 xhigh | GPT-5.4 xhigh | 4,889 | 0 (0.00%) | IoU@0.5 Accuracy `73.88` |

## Detailed Metrics And Artifacts

| Dataset | Split | Captioning model | Reasoning model | Supplementary metric(s) |
| --- | --- | --- | --- | --- |
| D-Cube | full | GPT-5.4 xhigh | GPT-5.4 xhigh | Pr. `51.22`, N-acc. `44.76` |
| GRefCOCO | testB | GPT-5.4 xhigh | GPT-5.4 low | gIoU `62.96` |
| GRefCOCO | testB | GPT-5.4 xhigh | GPT-5.4 xhigh | gIoU `62.78` |
| RefCOCO+ | testA | GPT-5.4 xhigh | GPT-5.4 low | mIoU `70.53` |
| RefCOCO+ | testA | GPT-5.4 xhigh | GPT-5.4 xhigh | mIoU `72.03` |
| RefCOCO+ | testB | GPT-5.4 xhigh | GPT-5.4 low | mIoU `62.43` |
| RefCOCO+ | testB | GPT-5.4 xhigh | GPT-5.4 xhigh | mIoU `65.35` |

## No-Target Sample Ratios

No-target samples are expressions whose ground truth has no corresponding object
in the image. They are central to GRefCOCO and D-Cube, and absent from the
reported RefCOCO+ splits. Counts below are computed from the prepared dataset
annotations used by each run: GRefCOCO/RefCOCO+ JSON rows and D-Cube D3 samples.

| Dataset / split | Total samples | No-target samples | Ratio |
| --- | ---: | ---: | ---: |
| D-Cube full | 42,102 | 29,067 | 69.04% |
| GRefCOCO testB | 14,933 | 4,242 | 28.41% |
| RefCOCO+ testA | 5,726 | 0 | 0.00% |
| RefCOCO+ testB | 4,889 | 0 | 0.00% |

## Notes

- D-Cube full xhigh reports official COCO-style bbox mAP over Full, Present,
  and Absent annotation profiles.
- GRefCOCO main metrics are `Pr.` and `N-acc.`; `gIoU` is supplementary.
- RefCOCO+ main metric is bbox `IoU@0.5 Accuracy`; `mIoU` is supplementary.
- Output directories contain the corresponding `evaluation.json`, match
  artifacts, run manifests, and config snapshots where available.
