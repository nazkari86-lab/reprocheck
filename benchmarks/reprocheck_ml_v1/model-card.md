# ReproCheck-ML model card

## Intended use

ReproCheck-ML prioritizes sentences that may contain measurable scientific claims. It is
an assistant for locating evidence, not a system that decides whether a scientific result
is true. Every final verdict remains deterministic and source-grounded.

## Frozen encoder

- Base encoder: `intfloat/multilingual-e5-small`
- Revision: `d1d99a1efae6779390caba937d92c54b5bc70e51`
- Architecture: 12 layers, 384-dimensional representations, approximately 0.1B parameters
- License: MIT
- Languages evaluated by this project: English (`en`), Russian (`ru`), Kazakh (`kk`)

The upstream model describes support for 100 languages but warns that low-resource
languages may perform worse. ReproCheck therefore reports each language separately and
does not infer Kazakh quality from an overall multilingual score.

## Training and evaluation contract

Training accepts only rows already assigned to the owner-disjoint `train` split. Model
selection and selective-decision thresholds use `validation` only. The frozen `test` and
prospective cohorts are evaluated once without adaptation. Every saved file, corpus,
split, configuration, seed, dependency version, and training row set is hash-bound in the
model manifest.

## Outputs and abstention

The model emits a claim-candidate probability, confidence, language, and an
out-of-distribution flag. Low confidence or an unsupported language forces review or
abstention. It cannot emit a final evidence verdict.

## Known limitations

- Long inputs are truncated to 256 tokens in the preregistered configuration.
- Confidence is not proof that a claim is correct.
- Kazakh is a required subgroup and may be the weakest subgroup.
- Repository authorship, domain shift, generated prose, and annotation ambiguity can
  change performance.
- No scientific performance claim is valid until the frozen external and prospective
  evaluations have been completed and published with confidence intervals.
