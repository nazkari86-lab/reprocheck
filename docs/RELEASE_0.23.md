# ReproCheck 0.23.0

Version 0.23.0 is the post-v7 development release.

- Preserves the fresh 0.22.0 zero-shot score: 1/4 cases and 5/11 claims.
- Adds `Mean Latency` table support with millisecond normalization.
- Extracts total and language-specific test counts from prose and tables.
- Extracts hashfile/artifact size comparisons as `artifact_size_mb` rather than
  conflating storage size with process memory.
- Rejects embedded model identifiers such as `FP16` as numeric precision values.

On the already inspected v7 cases, 0.23.0 reaches 3/4 and 9/11. That development
score is not a replacement for the frozen external result.
