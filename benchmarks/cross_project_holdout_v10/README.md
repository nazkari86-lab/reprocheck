# Cross-project holdout v10

This preregistered, source-unseen study evaluated frozen ReproCheck 0.24.0 on
public Markdown documents from repository owners excluded from every earlier
study. The registration was pushed at commit `9582949`; 20 eligible documents,
155 claim labels, and immutable source locks were pushed at commit `d7a9dc2`
before the extractor's first execution.

The frozen zero-shot result is **2/20 complete documents (10.0%)** and **32/155
claims (20.65%, Wilson 95% CI 15.02–27.69%)**. The preregistered 85% visibility
and 70% lower-bound thresholds were not met. This result is retained unchanged.

The result shows that 0.24.0 generalized poorly from correction-oriented
documents to broader real README result formats, especially arbitrary result
tables, benchmark console output, improvement prose, and metric families not
previously represented. Any development using v10 is post-inspection and cannot
replace `results/zero-shot-0.24.0.json`. A later version requires another fully
independent preregistered holdout.
