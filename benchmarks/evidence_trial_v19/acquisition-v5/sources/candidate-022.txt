# Three-Body Phase 16B - Radius Warning Re-Pose Results

Status: **complete 2026-05-29.** Phase 16B lands Branch A:
**warning verdict flips under `radius`**.

Phase 16B re-poses the Phase 15 warning-quality readout with `radius` as the
warning score, using the completed Phase 16 passive lock receipt. It is an
offline verdict-reconciliation pass only: no new simulation, no controller
retune, no new hazard label, and no revision of the Phase 15 Fail-Magnitude
mechanism verdict.

The verdict is already determined by Phase 16's committed per-cell column:
`radius` = `0.996624` with `27/27` favorable cells defined, while the within-16B
energy baseline = `0.655508` with `27/27` favorable cells defined. Phase 16B
formalized that number in Phase 15's verdict shape and adds no statistical
evidence beyond Phase 16's stronger pooled `radius` AUROC (`0.995136`).

Implementation receipt:

- [`PHASE16B_SPEC.md`](PHASE16B_SPEC.md)
- `scripts/threebody-phase16b-radius-warning.mjs`
- `npm run threebody:phase16b:repose`
- output directory: `results/threebody/phase16b-radius-warning-repose/`

Verification:

- `node --check scripts/threebody-phase16b-radius-warning.mjs` passed
- `package.json` parsed successfully
- reducer validated Phase 16 manifest branch `A_hazard_warnable`
- reducer reproduced Phase 16 per-cell values exactly to recorded precision

## Command

```powershell
npm run threebody:phase16b:repose
```

Result files:

- `radius-warning-quality-map.csv`
- `radius-warning-summary.csv`
- `manifest.json`

## Readback

Source receipt: `results/threebody/phase16-hazard-channel-audit-lock/`

Phase 16 source validation:

- Phase 16 branch: `A_hazard_warnable`
- passive trial count: `288`
- favorable pocket: `216` trajectories, `1,460` samples, `214` positive labels
- 16B decidability is stricter than Phase 15's historical coverage convention:
  a cell must contain both label classes for AUROC to be defined

Primary Phase-15-shaped readout (`dt=0.004` only):

| score | mean cell AUROC | defined cells | verdict |
|---|--:|--:|---|
| `radius` | **0.996624** | **27/27** | **PASS** |
| `energy` | 0.655508 | 27/27 | miss |

Branch: **A - warning verdict flips under radius.**

Per-velocity summary:

| scope | radius mean | energy mean | radius cells |
|---|--:|--:|--:|
| `v_0p95_control` | 0.804060 | 0.555479 | 9/9 |
| `v_1p05` | 0.990219 | 0.704489 | 9/9 |
| `v_1p1` | 1.000000 | 0.648918 | 9/9 |
| `v_1p15` | 0.999653 | 0.613118 | 9/9 |

## Interpretation

Phase 16B closes the warning-quality accounting in Phase 15's own verdict shape:
with `radius` substituted for energy, the warning bar clears decisively
(`0.996624 >= 0.70`, `27/27 >= 18/27`). Energy remains below bar on the same
`dt=0.004` slate (`0.655508`), so the Phase 15 warning miss was an
instrument-choice failure.

This does **not** add statistical evidence beyond Phase 16's stronger pooled
`radius` AUROC (`0.995136`), does **not** revise Phase 15's Fail-Magnitude
mechanism verdict, and does **not** retune the controller. It is a formal
warning-instrument repair: the strict-oracle hazard label was warnable, but
energy was the wrong instantaneous score.
