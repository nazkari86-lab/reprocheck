# Numeric mutation experiment amendment 1

The frozen v1 test was executed and preserved. The intended numeric-consistency feature
was encoded with a numeric level (`numeric-consistency-10`). The shared text normalizer
replaced that level with `<num>`, making full and partial consistency indistinguishable.
Consequently, the v1 hybrid and text-only models were effectively identical and both
reached test F1 0.6435.

V2 uses categorical words (`full`, `partial`, `none`) that survive normalization. It also
normalizes numbers before computing the lexical-overlap baseline, preventing that baseline
from directly reading the constructed mutation token. V2 uses a new seed and owner split
and must be registered and published before its test is executed. V1 remains immutable.
