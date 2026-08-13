# Cross-project holdout v13

V13 was preregistered and pushed before retrieval at commit `3c8b555`. The
registered retrieval then returned zero selected documents: every candidate in
the 30 top-100 search frames belonged to a repository or owner already present
in the exclusion corpus from v2-v12.

This is a sampling-frame exhaustion result, not an evaluation of ReproCheck
0.27.0. No labels were created and the evaluator was never run. The raw API
responses, deterministic candidate ordering, empty sample, and retrieval
summary are retained so that the failed study cannot be silently replaced.
