# Self-hosted throughput benchmark (one H100)

Measured with `vllm bench serve` against a vLLM server on a single H100-80GB, saturated
(`--request-rate inf --max-concurrency 256`, 500 prompts, `--ignore-eos`). Three self-hosted
models: Qwen3-30B-A3B and CoPE-B-A4B are ~3B-active MoE; **IBM Granite 3.3 8B is a dense 8B that
fits a 24GB consumer GPU** (measured here on the H100 for an apples-to-apples comparison — on a
24GB card the absolute numbers drop but the monolith-vs-atomic *ratio* holds). Token profiles are
each condition's measured input/output lengths from the 1,000-item run. Cost assumes **$2/hr**
for the H100. Dates: 2026-07-11 (Qwen, CoPE), 2026-07-19 (Granite).

## Results

**CoPE-B-A4B** (`zentropi-ai/cope-b-a4b`, ~3.8B active) — note monolith emits 1 token (native
binary mode), so its monolith is atypically fast:

| Condition (in/out) | Req/s | Decisions/s | **Decisions/hour** | **$/1k dec** | vs monolith |
|---|---|---|---|---|---|
| monolith (744/1) | 22.25 | 22.25 | ~80,100 | $0.025 | 1.0× |
| qa (239/38) | 51.09 | 51.09 | ~183,900 | $0.011 | 2.3× |
| atomic (117/6, ÷4) | 176.72 | 44.18 | ~159,000 | $0.013 | 2.0× |

**Qwen3-30B-A3B-Instruct** (~3B active) — a *general* model, so monolith emits a full JSON
label (32 tok); this is the more representative "self-host a general LLM" case:

| Condition (in/out) | Req/s | Decisions/s | **Decisions/hour** | **$/1k dec** | vs monolith |
|---|---|---|---|---|---|
| monolith (1156/32) | 12.25 | 12.25 | ~44,100 | $0.045 | 1.0× |
| qa (267/39) | 43.49 | 43.49 | **~156,600** | $0.013 | **3.6×** |
| atomic (118/6, ÷5) | 255.51 | 51.10 | **~184,000** | $0.011 | **4.2×** |

**IBM Granite 3.3 8B** (dense 8B, ~16GB bf16 — the "you don't need an H100" case; atomic here is
the tuned 5-question set, so **÷5 calls/decision**):

| Condition (in/out) | Req/s | Decisions/s | **Decisions/hour** | **$/1k dec** | vs monolith |
|---|---|---|---|---|---|
| monolith (1345/37) | 24.49 | 24.49 | ~88,200 | $0.023 | 1.0× |
| atomic (~160/8, ÷5) | 215.48 | 43.10 | **~155,100** | $0.013 | **1.8×** |

## The point

- **At saturation, policy-as-code is a throughput multiplier.** On a general model, qa serves
  **~3.6× the decisions/hour** of the bloat prompt (and atomic ~4.2×, because tiny per-question
  calls batch superbly) on the *same* GPU. The input-token cut we measured on the API side
  (~75%) reappears here as ~4× more decisions/hour (3.6× qa, 4.2× atomic) → ~4× lower cost per
  decision self-hosted.
- **Same silicon, more useful work.** Total token throughput is similar across conditions
  (~14–34k tok/s) — the GPU is equally busy. The difference is *what* the tokens buy: monolith
  burns them re-sending policy on every request; qa/atomic turn them into decisions.
- **Bigger gap on the general model** (3.6×) than on CoPE (2.3×), because CoPE's monolith emits
  only 1 token (no decode) while Qwen's monolith carries both a 4× larger prompt and real output.

## Assumptions (read before quoting these numbers)

1. **Content is short — ~24 tokens mean, 12 median** (p90 56, p99 183, max 227). These are
   posts/comments. **This is the load-bearing assumption:** the policy (~1,120 tok) dominates
   each monolith request, so shrinking it buys throughput. The win is *proportional to how much
   the policy dominates the input* — biggest for short content. If content were ~1,000 tokens,
   monolith(2,120) vs qa(1,230) is only a 1.7× input ratio, and the throughput gap would shrink
   from ~3.6× toward ~1.7×. So: **smaller policies help most when moderating short content.**
2. **Fixed per-request token profiles**, taken from our 1,000-item run averages
   (monolith 1156/32, qa 267/39, atomic 118/6 per call). Real traffic varies in length.
3. **Saturation numbers.** `--max-concurrency 256 --request-rate inf` pushes the server to its
   ceiling — these are *max* throughput. Production at lower load won't hit them, but the
   **relative** ratios (the comparison we care about) hold. TTFT is high here (queueing at max
   concurrency) and is NOT a production latency figure.
4. **Uniform lengths** (`--random` fixed len, no variance) and **`--ignore-eos`** (forces exactly
   output-len tokens) — for a clean, consistent measurement. Mixed real lengths batch slightly
   differently.
5. **One H100-80GB, bf16, one model resident, `--max-model-len 8192`.** Different GPU,
   quantization, or batch settings shift the absolute numbers.
6. **Cost = $/hr ÷ throughput**, at an assumed **$2/hr**. Self-hosting cost is fixed regardless
   of volume, so $/decision depends entirely on how busy you keep the GPU. Plug your real rate.
7. **atomic = N calls/decision** — decisions/hour = per-call req/s ÷ N. N=4 for CoPE (its shipped
   4-question set); N=5 for Qwen and Granite (their shipped 5-question sets). Qwen's atomic req/s
   was measured pre-prune at 4 calls; dividing the *same* per-call rate by the shipped 5 gives
   ~184K/hr (a ÷4 would overstate it as ~230K).
8. **CoPE/Qwen are ~3B-active MoE; Granite 3.3 8B is dense (8B active)** — the dense 8B is why
   Granite's atomic multiplier (1.8×) is smaller than Qwen's (4.2×): its monolith already decodes
   fast, so there's less headroom to reclaim. Larger/denser models are slower in absolute terms.
9. **Consistency:** every condition was measured identically (same GPU, concurrency, prompt
   count, saturation), so the relative comparisons are apples-to-apples even where the absolute
   numbers depend on the assumptions above.
10. **Two monolith profiles predate their shipped v2 policies.** Qwen's monolith was later
   strengthened (Section 8/9; benchmark 1156 → shipped ~1345 tok) and Granite's had its
   stance-check hoisted to Section 0 (benchmark 1345 → shipped ~1502 tok) *after* this benchmark.
   A larger monolith prompt only *lowers* monolith throughput, so those two monolith rows (Qwen
   ~44,100/hr, Granite ~88,200/hr) are a conservative *ceiling* — the true atomic-vs-monolith
   multiplier is if anything larger. Atomic profiles and CoPE/Gemini are unchanged.

## How to reproduce

On the pod (model already served):
```bash
export HF_HOME=/workspace/hf
vllm bench serve --backend openai-chat \
  --model <served-name> --tokenizer <hf-repo-id> \
  --base-url http://localhost:8000 --endpoint /v1/chat/completions \
  --dataset-name random --random-input-len <IN> --random-output-len <OUT> \
  --num-prompts 500 --max-concurrency 256 --request-rate inf --ignore-eos
```
Profiles used — CoPE: monolith `744/1`, qa `239/38`, atomic `117/6`;
Qwen: monolith `1156/32`, qa `267/39`, atomic `118/6`;
Granite 8B: monolith `1345/37`, atomic `160/8` (per question call).
