# Invalidated before scoring

This study is not external-validation evidence. During manual eligibility review, the
current parser was accidentally invoked on the source for the only apparent eligible
case before `labels.json` and `cases.json` were frozen. That violates the preregistered
blind-label order.

No score is reported and no result file exists. The registration, raw search responses,
frames, and deterministic sample remain committed so the failed procedure is auditable
and so every exposed pull request is excluded from later holdouts. The observed format
was treated only as development input.
