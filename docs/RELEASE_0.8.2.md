# ReproCheck 0.8.2

Version 0.8.2 is a release-infrastructure patch with no parser or audit
behavior change relative to 0.8.0.

- Excludes immutable third-party benchmark sources from Ruff formatting and
  lint discovery while continuing to check all project-owned Python code.
- Keeps the complete scientific gate mandatory before release publication.
- Preserves every frozen evaluator, annotation, and result artifact unchanged.
