# SciRIFF Summarization: Base vs LoRA Evaluation Report

## Objective

Compare **Qwen/Qwen2.5-3B-Instruct** against the same base with a SciRIFF summarization LoRA adapter on held-out scientific summarization. Report both **quality** (ROUGE, BLEU, METEOR, BERTScore) and **systems** (latency, tokens/sec) metrics, including vLLM serving.

## Dataset and split alignment

| Item | Value |
| --- | --- |
| Source | `allenai/SciRIFF`, config `4096` |
| Filter | `metadata.task_family == "summarization"` |
| Split | Official HF **`test`**, shuffle seed **42**, first **300** rows |
| Match to training | Same recipe as notebook `test_small` (see [`notebook/scientific_llm_finetuning_pipeline.ipynb`](../notebook/scientific_llm_finetuning_pipeline.ipynb)) |
| Eval file | `data/sciriff_summarization_eval.json` |

Training used train/val/test = 3000/300/300 from the official HF splits (not a single pooled reshuffle), so this eval set is held-out relative to training.

## Model and serving

| Setting | Value |
| --- | --- |
| Base | `Qwen/Qwen2.5-3B-Instruct` |
| Adapter | `adapters/sciriff_lora` (served as `sciriff-lora`) |
| LoRA | r=16, α=16, q/k/v/o + gate/up/down |
| Generation | greedy, `max_tokens=256` |
| vLLM | `max-model-len=2048`, `--enforce-eager`, `--gpu-memory-utilization 0.85` |
| Hardware | RTX 4060 Laptop 8GB (WSL) |

## Primary results: vLLM, n=300

### Quality

| Metric | Base | LoRA | Delta |
| --- | ---: | ---: | ---: |
| ROUGE-1 | 0.3452 | 0.3198 | −0.0253 |
| ROUGE-2 | 0.0884 | 0.0927 | +0.0043 |
| ROUGE-L | 0.1858 | 0.1959 | +0.0102 |
| ROUGE-Lsum | 0.2224 | 0.2188 | −0.0036 |
| BLEU | 0.0384 | 0.0442 | +0.0058 |
| METEOR | 0.2104 | 0.1945 | −0.0159 |
| BERTScore P | 0.0669 | 0.1365 | +0.0696 |
| BERTScore R | 0.0874 | 0.0421 | −0.0453 |
| BERTScore F1 | 0.0775 | 0.0886 | +0.0110 |

Source: [`outputs/metrics_vllm_extended.json`](../outputs/metrics_vllm_extended.json). BERTScore is baseline-rescaled.

### Systems

| | Base | LoRA |
| --- | ---: | ---: |
| Avg latency (s) | 6.04 | 7.01 |
| p50 (s) | 7.03 | 6.61 |
| p95 (s) | 7.80 | 12.01 |
| Tokens/sec | 34.6 | 20.7 |
| Avg completion tokens | 208.7 | 145.1 |
| Avg prediction words | 157.4 | 119.4 |
| Empty output rate | 0.0 | 0.0 |

Source: [`outputs/metrics_vllm_systems_n300.json`](../outputs/metrics_vllm_systems_n300.json) (derived from the predictions CSV; no re-inference).

### Interpretation

- **Structure / n-gram precision / semantics:** LoRA leads on ROUGE-L, ROUGE-2, BLEU, and BERTScore F1.
- **Unigram overlap / METEOR:** Base leads on ROUGE-1 and METEOR.
- **Length:** LoRA generations are shorter on average (fewer completion tokens), which can raise p95 latency variance while lowering mean tokens/sec.
- Gains are **modest**; treat as a successful specialization signal, not a large absolute jump.

## Charts (vLLM n=300)

![Quality overview](quality_overview_vllm_base_vs_lora.png)

![ROUGE](rouge_vllm_base_vs_lora.png)

![BLEU / METEOR / BERTScore](text_metrics_vllm_base_vs_lora.png)

![BERTScore](bertscore_vllm_base_vs_lora.png)

![Output length](output_length_histogram_vllm.png)

![Length scatter](length_scatter_vllm.png)

## Qualitative examples

Examples with the largest LoRA ROUGE-L gains on the n=300 set (excerpts truncated).

### Example 278

**Reference:** we study the @xmath0 and @xmath1 signatures @xmath2 for different values of @xmath3 in the msugra model . with @xmath3 rising , we observe a characteristic change in the shape of dilepton mass spectra...

**Base:** Abstract-style rewrite about LHC / SUSY (lower overlap with the reference phrasing).

**LoRA:** Closely follows the reference scientific abstract style and wording (ROUGE-L ≈ 0.94 vs base ≈ 0.17).

### Example 141

**Reference:** backgroundmalaria control programmes utilising indoor residual spraying...

**Base:** Generic abstract rewrite about IRS / malaria monitoring.

**LoRA:** Stays closer to the reference control-programme wording (ROUGE-L ≈ 0.91 vs base ≈ 0.33).

## Appendix A — Path A HF smoke (n=10)

Local Hugging Face generate (single GPU), same seed/filter, first 10 of the eval set.

| Metric | Base | LoRA | Delta |
| --- | ---: | ---: | ---: |
| ROUGE-1 | 0.2615 | 0.2850 | +0.0235 |
| ROUGE-2 | 0.0619 | 0.0559 | −0.0060 |
| ROUGE-L | 0.1457 | 0.1824 | +0.0367 |
| BLEU | 0.0161 | 0.0151 | −0.0010 |
| METEOR | 0.1355 | 0.1549 | +0.0194 |
| BERTScore F1 | −0.0007 | −0.0159 | −0.0153 |
| Avg latency (s) | 8.21 | 13.32 | +5.10 |

Absolute scores differ from vLLM (decoding path, length, truncation). Use **within-path** Base vs LoRA deltas; do not over-interpret cross-backend absolute ROUGE.

## Appendix B — HF → vLLM systems smoke (n=10)

| | HF | vLLM | Speedup |
| --- | ---: | ---: | ---: |
| Base avg latency | 8.21 s | 6.63 s | ~1.24× |
| LoRA avg latency | 13.32 s | 5.44 s | ~2.45× |

Source: [`outputs/metrics_vllm_base_vs_lora.json`](../outputs/metrics_vllm_base_vs_lora.json) (smoke run). Serving removes most of the HF LoRA latency penalty on this hardware.

## Reproducibility notes

- Greedy decoding and fixed seed 42.
- Prompts truncated client-side so chat template + `max_tokens` fit `max_model_len=2048`.
- Metric packages: `rouge-score`, `sacrebleu`, `nltk` (METEOR), `bert-score` (rescaled).
- Serve: [`vllm/serve_lora.sh`](../vllm/serve_lora.sh). Client smoke: [`vllm/test_client.py`](../vllm/test_client.py).
