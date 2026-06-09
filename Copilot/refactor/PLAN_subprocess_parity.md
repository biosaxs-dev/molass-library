# Plan: Subprocess Parity — GUI Path Missing ip_*.npy Export

**Issue**: molass-library#206  
**Status**: Open  
**Last updated**: Jun 9, 2026

---

## Background

Issues #38–#42 (molass-legacy) established in-process/subprocess parity for BH:
- `ip_xr_elcurve_y.npy`, `ip_uv_elcurve_y.npy` — EGH-fitted elution curves (#38)
- `ip_xr_D.npy`, `ip_uv_U.npy` — 2D intensity matrices (#39)
- `ip_xr_E.npy` — error matrix (#40)
- `ip_xr_qvector.npy` — trimmed q-values (966 vs 972 elements) (#41)
- `FixedBaselineOptimizer` removed from subprocess default (#42)

Result: BH subprocess delta_fv < 0.001 for **notebook→subprocess** path.

---

## New observation (Jun 9, 2026)

DE with `in_process=True` (notebook): **SV ≈ 84.37**  
DE with `in_process=False` (GUI subprocess): **SV ≈ 78.56** — ~5.8 SV gap

Confirmed on analysis-020: `optimized/` folder has **no ip_*.npy files**.

---

## Root cause

There are two distinct code paths:

**Path B (notebook → subprocess)** — *fixed by #38–42*:
```
decomp.optimize_rigorously(in_process=False)
  → make_rigorous_decomposition_impl()
    → prepare_rigorous_folders()   ← writes ip_*.npy ✅
      → BackRunner.run()           ← subprocess reads ip_*.npy ✅
```

**Path C (GUI)** — *not fixed*:
```
GUI click → BackRunner.run()
              → OptimizerMain.create_optimizer_from_job()
                → get_sd_from_folder_impl()   ← legacy disk load, no ip_*.npy ❌
```

`prepare_rigorous_folders` is **never called** in Path C.  
All 7 parity overrides silently skip → subprocess uses legacy-derived data.

---

## Divergence factors (all 8, now clearly mapped)

| # | Factor | Override file | Loaded in | Fixed for Path B | Fixed for Path C |
|---|---|---|---|---|---|
| 1 | XR elution curve y | `ip_xr_elcurve_y.npy` | `OptDataSets.get_dsets_impl` | ✅ #38 | ❌ |
| 2 | UV elution curve y + sy | `ip_uv_elcurve_y.npy` | `OptDataSets.get_dsets_impl` | ✅ #38+#51 | ❌ |
| 3 | XR D matrix | `ip_xr_D.npy` | `OptDataSets.get_dsets_impl` | ✅ #39 | ❌ |
| 4 | UV U matrix | `ip_uv_U.npy` | `OptDataSets.get_dsets_impl` | ✅ #39 | ❌ |
| 5 | E matrix | `ip_xr_E.npy` | `OptDataSets.__init__` | ✅ #40 | ❌ |
| 6 | qvector | `ip_xr_qvector.npy` | `OptimizerMain.create_optimizer_from_job` | ✅ #41 | ❌ |
| 7 | FixedBaselineOptimizer | (removed) | `optimizer_main` | ✅ #42 | ✅ #42 |
| **8** | **Rg curve smoothness** | `rg-curve/` (library vs legacy) | `GuinierDeviation` in objective | ⚠️ Changed | ❌ |

**Factor 8 details (hypothesis — to be investigated)**:  
The Jun 8 "Complementary View → Plot Components" refactor (`molass-legacy@7f96055`) changed
`PeakEditor.prepare_rg_curve()` to use `ssd.get_rg_curve()` (library estimator) instead of
the previous legacy `fullopt_input.get_dsets(compute_rg=True)` path. The resulting Rg curve
is exported to `rg-curve/` which `GuinierDeviation` reads in the subprocess objective.

If the library Rg curve is **less smooth** than the legacy one, `Guinier_deviation`
oscillates more → rougher landscape → DE (population-based, sensitive to landscape noise)
converges prematurely; BH (local NM descent) averages over the noise.

**Factor 8 investigation result (Jun 9, 2026)**:

Rg quality comparison on the same dataset:
- GUI `rg-curve/` (library, post-Jun-8 refactor): n=121, mean=0.813, median=0.948, >0.8: 74%
- Notebook `rg_curve_parent/` (library via `prepare_rigorous_folders`): n=112, mean=0.756, median=0.959, >0.8: 71%

**Conclusion: Rg smoothness is NOT the primary cause of the DE SV gap.** Quality distributions
are similar (both library path). The ~5.8 SV gap is dominated by Factors 1–6 (missing
ip_*.npy files). The Jun 8 Rg unification refactor is not the culprit.

Note: analysis-020 BH (GUI subprocess, no ip_*.npy) also gives SV≈78.56 — the same gap
that BH had before issues #38–42 were fixed. This confirms the gap is caused by missing
ip_*.npy, not by Rg curve quality.

---

## Fix options

### Option A — Export ip_*.npy from the GUI side (shallow fix)

In the GUI launch flow (before `BackRunner.run()`), reconstruct a library `SecSaxsData`
from the loaded analysis folder and call a lightweight version of `prepare_rigorous_folders`
that writes only the ip_*.npy files.

**Location**: `NaviFrame.py` or wherever `prepare_batch` is called before `BackRunner`.

**Pro**: Minimal code change, reuses existing export machinery.  
**Con**: Requires `ssd` construction from `sd` in the GUI path (~10s overhead before optimizer starts).

### Option B — Deep fix (unify paths)

Refactor the GUI to go through `make_rigorous_decomposition_impl` directly, same as the
notebook path. The GUI creates a `Decomposition` object, then calls `optimize_rigorously(in_process=False)`.

**Pro**: Single code path, parity guaranteed forever.  
**Con**: Large refactor of GUI flow.

### Option C — Immediate value: in-process checkbox in GUI

Add a checkbox "Run in process (recommended for DE/NSGA2)" to the GUI strategy dialog.
When checked, uses `InProcessRunner` directly — already tested and working.

**Pro**: Zero data-quality issue (in-process uses parent data directly); users can choose.  
**Con**: Users need to understand the tradeoff.

---

## Recommended order

1. **Option C first** (low risk) — add in-process checkbox to strategy dialog
2. **Option A second** — fix subprocess data quality so both paths are equivalent
3. **Option B long-term** — full path unification (requires `sd → ssd` consolidation)

---

## Testing

Once Option A is implemented, verify by:
1. Run BH from GUI on a fresh analysis folder
2. Confirm `ip_*.npy` files exist in `optimized/`
3. Run DE from GUI — expect SV comparable to `in_process=True` (≥84)
4. delta_fv between subprocess and in-process should be < 0.01
