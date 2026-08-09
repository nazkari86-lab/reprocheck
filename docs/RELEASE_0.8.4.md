# ReproCheck 0.8.4

Version 0.8.4 is a release-verification patch with no parser or audit behavior
change relative to 0.8.0.

- Writes portable checksum entries using asset basenames rather than build
  directory paths.
- Verifies the generated checksum manifest before publishing any release.
- Preserves every frozen evaluator, annotation, and result artifact unchanged.
