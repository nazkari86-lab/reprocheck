# ReproCheck 0.30.4

ReproCheck 0.30.4 fixes the third fail-closed acquisition integration defect while
preserving the entire failed run.

Generation 4 successfully materialized nine commit-pinned candidates, then GitHub
returned a search response truncated inside a JSON string. The runner froze those bytes
before semantic validation and therefore could not safely resume. Its registration,
nine candidates, 31 response files, state, and failure manifest remain frozen under
`registration-v4-failed.json` and `acquisition-v4/`; none are used as study data.

Generation 5 checks response size, declared `Content-Length`, UTF-8 JSON completeness,
and object shape before bytes enter immutable acquisition state. Incomplete transport is
retried up to three times. The generation uses a new selection salt and freezes the
reproducible 0.30.4 evaluator wheel with SHA-256
`ce047d763c1bb6b91c49c2f5effee9b432e5b7b1b15d6e1d1149ac2ccb1a99f0`.

Scientific status: generation 5 is registered and initially unexecuted. Earlier partial
runs are engineering failure evidence only.
