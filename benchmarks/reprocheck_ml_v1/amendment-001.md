# Amendment 001 — domain-balanced discovery

Date: 2026-08-21

The registered v1 discovery was executed without opening repository contents or running
ReproCheck. It reached 120 unique owners but stopped before the third search frame,
yielding 63 computer-vision, 57 NLP, and 0 other-ML repositories. This contradicts the
declared domain-coverage objective and makes that discovery unsuitable as the primary
confirmatory development cohort.

The original registration (`d533d66d…`) and output (`fe304f06…`) remain immutable and
public. No selected report, annotation, model score, or verifier outcome was inspected
before this amendment.

Version 2 changes only the metadata-stage stopping rule: it requires exactly 40 unique
owners from each of the three frozen frames, for 120 total. License, fork, archive,
owner-deduplication, query, and ordering rules are unchanged. A new registration is
created before executing v2 discovery.
