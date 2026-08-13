# Cross-project holdout v11

This is the first prospective external-generalization study for ReproCheck
0.25.0 after v10 development. The registration was pushed in commit `f711ad6`.
All 64 new sources and the 25-document, 237-claim manual label set were hashed,
committed, and pushed in `050eb2e` before ReproCheck was run.

The single frozen zero-shot evaluation produced:

- complete documents: 1/25 (4.0%; Wilson 95% CI 0.7%-19.5%);
- visible selected claims: 38/237 (16.0%; Wilson 95% CI 11.9%-21.2%);
- preregistered success condition: not met.

This is an immutable negative result. It shows that the 100% v10 development
coverage did not establish broad external generalization. Unsupported v11
families include result-dense prose, console and box-drawing tables, scoped
metrics, hardware/network units, and multiple values sharing one line. Any
post-v11 improvement is development evidence and requires another independent
holdout before it can support a new zero-shot generalization claim.

