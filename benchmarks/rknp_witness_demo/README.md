# RKNP witness demo

This is an author-designed controlled demonstration, not an independent
evaluation corpus. `make rknp-demo` builds and verifies three distinct witness
rules:

- the main report claims 50% accuracy while its metric source records 93.3333%;
- the conflict case supplies 90% accuracy while predictions recompute to 50%;
- the split case reuses identity `id=1` across train and test.

The exact-split verifier reopens both CSV files and recomputes the overlap. The
demo does not establish natural defect prevalence or human time savings.
