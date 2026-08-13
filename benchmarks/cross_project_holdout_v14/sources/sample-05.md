# Optimized Pipeline Performance Results

## Variables Created
| Variable | Type | Shape | Description |
|---|---|---|---|
| `optimised_retention` | `DataFrame` | 409,287 × 74 | Dtype-optimised event log, ready for Feature Engineering |
| `performance_comparison` | `DataFrame` | 6 × 4 | Baseline vs. Optimised comparison table (Metric / Baseline / Optimised / Improvement) |
| `BG`, `TEXT`, `SUBTLE`, `GOLD`, `GREEN`, `BLUE`, `ORANGE` | `str` | — | Zerve design system colour constants, propagated to all downstream blocks |
| `fig`, `axes`, `ax1`, `ax2`, `ax3` | matplotlib objects | — | 3-panel comparison chart |
| `fig2`, `ax4` | matplotlib objects | — | Dtype distribution chart |

## Confirmed Performance Results

| Metric | Baseline | Optimised | Improvement |
|---|---|---|---|
| **Columns** | 107 | **74** | **−33 cols (31% reduction)** |
| **Memory (deep, MB)** | 577.5 | **228.1** | **−349.4 MB (61% reduction)** |
| **Null analysis time (s)** | 0.145 | 0.041 | **3.5× faster** |
| **Cardinality analysis time (s)** | 0.671 | 0.412 | **1.6× faster** |
| **Skew analysis time (s)** | 0.129 | 0.051 | **2.5× faster** |
| **Total pipeline time (s)** | 1.895 | 0.512 | **3.7× faster** |

**Rows preserved**: 409,287 / 409,287 — **100% data fidelity maintained** (no rows dropped at any step)

## Dtype Transformation Summary
- **13 float64 columns → float32** (50% memory reduction per column)
- **0 integer columns** met the safe downcast threshold (all `int32` values were within range; no int64 present)
- **37 low-cardinality string columns → category** dtype (e.g., `event`, `prop_$lib`, `prop_$timezone`, `prop_$os`, `prop_$device_type`, `prop_$browser`, `prop_$geoip_country_code`, and 30 others)
- **33 redundant columns dropped** (`Unnamed: 0` + 16 `prop_$set.*` + 16 `prop_$set_once.*`)

## Files Saved
- `optimised_comparison.png` — Side-by-side Baseline vs. Optimised bar chart across memory, column count, and 3 stage timings (96.4 KB)
- `dtype_comparison.png` — Before/after dtype distribution grouped bar chart (54.5 KB)

## Interpretation
The 61% memory reduction from 577.5 MB → 228.1 MB is achieved without any loss of analytical columns. Every feature required for the 23-column user-level matrix (session IDs, event types, Python version, tool names, credit amounts, canvas pathnames) is preserved in `optimised_retention`. The 3.7× pipeline speedup directly accelerates the groupby aggregations in the Feature Engineering block.
