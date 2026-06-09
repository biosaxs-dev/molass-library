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

## Divergence factors (all 7, now clearly mapped)

| # | Factor | Override file | Loaded in | Fixed for Path B | Fixed for Path C |
|---|---|---|---|---|---|
| 1 | XR elution curve y | `ip_xr_elcurve_y.npy` | `OptDataSets.get_dsets_impl` | ✅ #38 | ❌ |
| 2 | UV elution curve y + sy | `ip_uv_elcurve_y.npy` | `OptDataSets.get_dsets_impl` | ✅ #38+#51 | ❌ |
| 3 | XR D matrix | `ip_xr_D.npy` | `OptDataSets.get_dsets_impl` | ✅ #39 | ❌ |
| 4 | UV U matrix | `ip_uv_U.npy` | `OptDataSets.get_dsets_impl` | ✅ #39 | ❌ |
| 5 | E matrix | `ip_xr_E.npy` | `OptDataSets.__init__` | ✅ #40 | ❌ |
| 6 | qvector | `ip_xr_qvector.npy` | `OptimizerMain.create_optimizer_from_job` | ✅ #41 | ❌ |
| 7 | FixedBaselineOptimizer | (removed) | `optimizer_main` | ✅ #42 | ✅ #42 |

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
