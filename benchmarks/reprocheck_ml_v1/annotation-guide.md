# ReproCheck-ML v1 Annotation Guide

Status: development guide; no hidden or prospective labels exist yet.

## Eligible claim

Label a block positive only when it reports a numerical model or system result in the
declared metric ontology. The annotation must bind an exact metric span and an exact
numeric span. Years, versions, model sizes, hyperparameters, counts without a result
metric, citations, and aspirational targets are negative examples.

## Claim tuple

Record `metric`, `value`, `unit`, and any explicitly stated `model`, `dataset`, `split`,
`task`, `experiment`, `run`, or `variant`. Never infer a missing context field. Every
positive block requires independent agreement or documented adjudication.

## Evidence pair

Mark an artifact compatible only when every populated shared context field agrees and
the artifact can support deterministic recomputation or structured comparison for the
claim metric. A plausible filename is not evidence. Every evidence-pair label requires
independent agreement or adjudication.

## Disagreements

Use `unresolved` until adjudication is complete. Unresolved positive blocks and evidence
pairs are rejected by the dataset validator and cannot enter training or evaluation.

## Prohibited leakage

Do not move blocks, translations, templates, forks, mirrors, repositories, or owners
across splits. Do not inspect hidden or prospective labels while changing the ontology,
model, prompts, features, thresholds, or evaluator.

