# ReproCheck 0.29.0

ReproCheck 0.29.0 improves portable extraction of independently written result
files. It recognises explicit result labels and units more consistently,
including percentile latencies, grouped numbers, nanoseconds and microseconds,
measured request rates, and metric-value prose. It also rejects table targets,
status text, deltas and denominator counts when those are not reported results.

The changes were developed against the already frozen v15 set. Its negative
0.28.0 evaluation remains unchanged; post-inspection v15 diagnostics are not
zero-shot evidence. A separate v16 registration will test this release using
new repositories, owners, query frames, source bytes, labels, and a locked
evaluator before the first evaluation.
