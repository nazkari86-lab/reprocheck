# ReproCheck 0.8.3

Version 0.8.3 is a CI reproducibility patch with no parser or audit behavior
change relative to 0.8.0.

- Pins direct CI dependencies so the scientific gate cannot change when a
  formatter, type checker, test runner, or runtime dependency publishes a new
  release.
- Retains the immutable-source lint boundary introduced in 0.8.2.
- Preserves every frozen evaluator, annotation, and result artifact unchanged.
