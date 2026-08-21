# ReproCheck-ML benchmark

Status: **protocol and implementation ready; authentic corpus not yet collected; no ML
performance result exists.** This wording must remain until the registered experiment is
completed.

Workflow:

1. Freeze `protocol.json`, `source-frame.json`, `exclusions.json`, schemas, and scripts
   with `python register.py --output registration.json`.
2. Verify the lock with `python verify-registration.py registration.json`.
3. Acquire immutable public sources and record every exclusion.
4. Annotate independently, adjudicate disagreements, and validate source spans/hashes.
5. Build the owner-disjoint split and reject exact/near leakage.
6. Train on `train`, calibrate on `validation`, then freeze the model.
7. Run hidden `test` once. Acquire prospective owners only afterward.

The scripts are thin, auditable entry points to the tested package functions. See the
project design document for annotation, review, and reporting details.
