# Evidence-layer ablation v1

This directory freezes the deterministic summary of the 19-case information
ablation documented in `docs/EVIDENCE_ABLATION.md`.

```bash
make evidence-ablation
```

`baseline-v1.json` includes the complete detection matrix, system summaries,
Wilson intervals, and paired exact McNemar results. The checker fails if any
case, result, version, or scientific-boundary text changes without an explicit
baseline review.

This is controlled development evidence. It is not described as blinded,
independent, natural-prevalence, or real-world accuracy evidence.
