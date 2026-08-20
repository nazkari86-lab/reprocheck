# Evaluation Framework

## Overview

AgriPerceiver's evaluation framework measures model quality across **structural validity**, **classification accuracy**, **regression quality**, **semantic similarity**, **calibration**, and **expert-level judgment** — reflecting the multi-dimensional nature of structured diagnostic output.

## Metric Suite

### 1. Structural Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **JSON Validity** | Fraction of outputs parseable as valid JSON | ≥ 0.95 |
| **Schema Compliance** | Fraction containing all 7 required fields | ≥ 0.90 |

### 2. Classification Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Type Macro F1** | F1 across 6 pathology types (fungal, bacterial, viral, pest, deficiency, unknown) | ≥ 0.70 |
| **Type Weighted F1** | Prevalence-weighted F1 | ≥ 0.75 |
| **Diagnosis Exact Match** | Normalized string equality | ≥ 0.50 |
| **Diagnosis Fuzzy Match** | Token-overlap Jaccard ≥ 0.6 threshold | ≥ 0.65 |

### 3. Regression Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Severity MAE** | Mean absolute error on [0, 1] severity scale | ≤ 0.15 |
| **Severity RMSE** | Root mean squared error | ≤ 0.20 |
| **Pearson r** | Correlation between predicted and true severity | ≥ 0.70 |

### 4. Calibration

| Metric | Description | Target |
|--------|-------------|--------|
| **ECE** | Expected Calibration Error (10 bins) | ≤ 0.10 |

### 5. Semantic Similarity (BERTScore)

| Field | Description | Target F1 |
|-------|-------------|-----------|
| **Symptoms** | Per-symptom best-match BERTScore | ≥ 0.70 |
| **Reasoning** | Full reasoning field comparison | ≥ 0.65 |

### 6. Composite Score

Weighted combination of all metrics (higher = better):

| Component | Weight |
|-----------|--------|
| Type F1 | 0.20 |
| Diagnosis Match | 0.15 |
| Symptom BERTScore | 0.15 |
| Severity (1 - MAE) | 0.10 |
| Reasoning BERTScore | 0.10 |
| Action BERTScore | 0.10 |
| JSON Validity | 0.10 |
| Schema Compliance | 0.05 |
| Calibration (1 - ECE) | 0.05 |

## Baseline Comparisons

Three baselines with comparable or larger parameter counts:

| Model | Parameters | Type |
|-------|------------|------|
| **Gemma-3-12B-IT** | 12B | General-purpose multimodal |
| **LLaVA-NeXT-7B** | 7B | General VLM (Mistral backbone) |
| **InternVL2-8B** | 8B | General VLM |

All baselines receive the same prompt requesting structured JSON output. This tests whether a lightweight domain-specialist (AgriPerceiver, ~4.3B total) can outperform larger general-purpose models on agricultural pathology.

## LLM-as-Judge Evaluation

Multi-judge consensus system scoring on 5 axes (1-5 each):

1. **Diagnostic Accuracy** — Is the disease identification correct?
2. **Completeness** — Are all symptoms, reasoning, and actions present?
3. **Reasoning Quality** — Is the pathological reasoning sound?
4. **Actionability** — Are treatments practical and correct?
5. **Clinical Reliability** — Would a plant pathologist trust this report?

Inter-judge agreement is measured via score variance across judges.

## Running Evaluation

```bash
# Full evaluation with metrics
agri-eval --predictions preds.jsonl --ground-truth gt.jsonl --output results.json

# Single image inference
agri-predict --image leaf.jpg --checkpoint checkpoints/specialist_e3.pt
```

### Predictions JSONL format
```json
{"image_path": "test_images/leaf_001.jpg", "output": "{\"diagnosis\": ...}"}
```

### Ground Truth JSONL format
```json
{"image_path": "test_images/leaf_001.jpg", "report": {"diagnosis": "...", "type": "...", ...}}
```
