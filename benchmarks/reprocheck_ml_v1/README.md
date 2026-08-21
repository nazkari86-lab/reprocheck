# ReproCheck-ML benchmark

Status: **protocol and implementation ready; authentic corpus not yet collected; no ML
performance result exists.** This wording must remain until the registered experiment is
completed.

Workflow:

1. Freeze `protocol.json`, `source-frame.json`, `exclusions.json`, schemas, and scripts
   with `python register.py --output registration.json`.
2. Verify the lock with `python verify-registration.py registration.json`.
3. Run `python acquire.py discover --output discovery.json` to acquire immutable
   repository heads from the frozen search frames and record every metadata exclusion.
4. Run `python acquire.py verify-discovery --discovery discovery.json` before inspecting
   repository contents.
5. Materialize supported report/evidence files, then annotate independently, adjudicate
   disagreements, and validate source spans/hashes.
6. Build the owner-disjoint split and reject exact/near leakage.
7. Train on `train`, calibrate on `validation`, then freeze the model.
8. Run hidden `test` once. Acquire prospective owners only afterward.

The scripts are thin, auditable entry points to the tested package functions. See the
project design document for annotation, review, and reporting details.
