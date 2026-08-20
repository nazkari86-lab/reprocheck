# ReproCheck 0.30.2

ReproCheck 0.30.2 fixes the first fail-closed external acquisition attempt without
rewriting its evidence.

GitHub code-search items do not include `default_branch`. The generation-2 parser
therefore rejected every otherwise usable item before a later request received HTTP
403. Generation 2, its ten raw responses, acquisition state, and failure manifest remain
frozen under `acquisition-v2/`; no candidate source was materialized.

Generation 3 retrieves repository metadata as a separately hashed response before it
resolves the default-branch commit and source bytes. It also uses a new deterministic
selection salt, validates the added `default_branch` candidate field, and freezes the
reproducible 0.30.2 evaluator wheel with SHA-256
`169c5945c4a68024d6eacce23855559b9cc0484b16c3d59cc655a4a82fb3ac3a`.

Scientific status: generation 3 is registered and initially unexecuted. Generation 2 is
a documented acquisition failure, not an external evaluation result.
