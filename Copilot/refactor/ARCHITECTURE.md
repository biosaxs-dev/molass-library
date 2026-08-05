# Architecture: Repository Role Separation

**Source**: Rule 13 of `Copilot/copilot-guidelines.md`  
**Last updated**: Aug 2026

---

## Target dependency direction

```
Original plan:  molass-library (computation) ← molass-legacy (GUI)
New perspective: molass-library (computation) ← molass-gui (GUI, clean Tkinter)
                                               molass-legacy (bridge/legacy → archive)
```

The original plan expected molass-legacy to become the long-term GUI home after shedding its
computation. That changed in Aug 2026 when **molass-gui** was created as a clean Tkinter GUI.
molass-legacy is no longer the future GUI; it is now a transitional bridge/dependency that
gradually shrinks as its computation migrates to molass-library.

- **`molass-gui`** — the **new GUI layer** (clean Tkinter, no computation). Calls
  `optimize_rigorously()` and receives `RunInfo` back. Has no subprocess infrastructure.
- **`molass-legacy`** — a **transitional bridge**: its tkinter GUI remains in maintenance mode;
  its optimizer infrastructure (BasicOptimizer, BackRunner, InProcessRunner, subprocess entry
  points) is the target of Level C migration to molass-library. Legacy-only code not called
  by any active path can be left as-is for reference.
- **`molass-library`** — the home for **all active computational code**: models, estimators,
  optimizers, data objects, algorithms, and eventually **all subprocess infrastructure**.

**When to act**: Refactoring should happen incrementally — when a relevant need arises
(fixing a bug, adding a feature, unifying a duplicated algorithm). Do not refactor
speculatively. Each step must leave both repos in a working state.

---

## Migration levels (sequential track)

| Level | Scope | Status |
|---|---|---|
| **A — Estimators** | Legacy estimators delegate to library for all init logic | ✅ Complete (SDM, EDM, CEDM, EGH peak recognition) |
| **B — Physical models** | `egh`, `edm_impl`, SDM/LKM model equations moved to library | ⏳ Not started |
| **C — Optimizer** | All optimizer infrastructure moved to library (see below) | ⏳ Not started — requires circular-import surgery |

Levels B and C require careful circular-import analysis before execution.

### Level C scope (updated Aug 2026)

Under the new perspective, Level C covers the full subprocess infrastructure — not just
`BasicOptimizer` and `InProcessRunner`, but all subprocess entry points:

| Component | Current location | Level C target |
|-----------|-----------------|----------------|
| `BasicOptimizer` | molass-legacy | molass-library |
| `InProcessRunner` | molass-legacy | molass-library |
| `BackRunner` | molass-legacy | molass-library |
| `optimizer.py` (subprocess entry) | molass-legacy | molass-library |
| `optimizer_recipe.py` (recipe entry) | molass-legacy | molass-library |

`optimizer_recipe.py` (added Aug 2026, Option E recipe-based subprocess) was written using
only molass-library API for the SSD pipeline, making its eventual migration straightforward.

---

## Data object consolidation (parallel track)

The legacy `sd` (`SerialData`) and the library `ssd` (`SecSaxsData`) represent the same
concept at different stages of development. Long-term goal: `ssd` fully replaces `sd`
as the authoritative data container, with the GUI eventually constructing and accepting
`ssd` directly.

This is a larger refactor than A–C because `sd` is deeply embedded in the legacy GUI's
internal data flow.

**Incremental steps**: identify GUI paths that construct or pass `sd`, replace them one
by one with `ssd` equivalents.

**Completed steps**:
- `PeakEditor` / `JobStateCanvas`: "Complementary View" replaced by library `plot_components_impl`
  (Jun 2026 — see `DESIGN_complementary_view_refactor.md`)
- `PeakEditor.prepare_rg_curve`: replaced `make_ssd_from_sd(self.sd)` (0-based jv) with
  `SSD(in_folder).trimmed_copy()` (absolute jv from filenames) — molass-legacy commit `ea94c36d`

### Design principle: absolute frame coordinates

**Principle (established 2026-07-31)**: Frame numbers (coordinates) must always reflect the
original untrimmed dataset's file numbering — not relative to any trimmed sub-range.

**Rationale**: When a trimmed or processed SSD is passed between components, each component
should be able to refer to the same physical frame using the same number. 0-based jv
introduces implicit offsets that cause frame mismatches (root cause of the SSD-native fix
and the EghEstimator UV height bug, see 33m).

**Current state vs. goal**:

| Component | Current state | Goal |
|-----------|--------------|------|
| `molass-library` SSD | ✅ absolute jv from filenames | Already correct |
| `molass-legacy` SerialData | 0-based `jvector` + `start_file_no` offset | Convert to absolute at load time |
| `molass-legacy` DataSet | 0-based `xr_ex` (compatibility alias `jvector` added #90) | Absolute at construction |
| `make_ssd_from_sd` bridge | `np.arange` (always 0-based) | Use `start_file_no` offset, or eliminate |
| Trim/restrict info | 0-based offsets | Absolute frame numbers |

**When to act**: Apply this principle one component at a time when a relevant fix or feature
touches that component. Do not refactor speculatively.

---

## Verification framework: GuiSimUtils

Each migration step must be verifiable without opening Tkinter. The canonical tool is:

```python
from molass_legacy.Test.GuiSimUtils import MockEditor, SimpleLrfSource, evaluate_init
```

- **`MockEditor`** — provides exactly the `PeakEditor` interface that legacy estimators
  expect, without a `SerialData` object or a Tkinter window. Works for all models.
- **`SimpleLrfSource`** — wraps a library `Decomposition` into the `peak_params_set`
  interface that `get_peak_params_advanced` reads.
- **`evaluate_init(optimizer, init_params, label)`** — calls `prepare_for_optimization`
  + `objective_func`, prints fv/SV/sigmas/seccol/Rgs.

**Workflow for each refactoring step**:
1. Run the legacy GUI path via `MockEditor` + legacy estimator → record SV
2. Run the library path directly (e.g., `decomp.make_rigorous_initparams()`) → record SV
3. If both SVs match within ±2, the migration is consistent

**Notebooks** (in `molass-researcher/experiments/33_gui_consistency/`):
- `33a_egh_model.ipynb` ✅ — EGH consistency (template for the series)
- `33b_sdm_model.ipynb` — SDM consistency
- `33c_lkm_model.ipynb` — LKM consistency
- `33x_gui_simulation.ipynb` — EGH debug history / prototype reference

---

## Subprocess parity (orthogonal issue)

The legacy GUI always uses `in_process=False` (subprocess via `BackRunner`). The subprocess
re-derives data from disk, bypassing the library's prepared data. This causes a ~5–6 SV
gap for new solvers (DE, NSGA2).

**Option E (Aug 2026)**: molass-gui uses a recipe-based subprocess (`optimizer_recipe.py`)
that rebuilds SSD from recipe parameters rather than legacy SD + .npy patches. This avoids
the parity problem entirely for new GUI users. The checkbox is opt-in; in_process=True
remains the default for notebook users.

See `PLAN_subprocess_parity.md` for the full analysis and fix options.
