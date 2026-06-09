# Design: Replace ComplementaryView with plot_components

**Discussed**: 2026-06-05  
**Status**: Planning complete, implementation deferred

---

## Goal

Replace the legacy `ComplementaryView` dialog (the "▽ Complementary View" button in `PeakEditor`) with the library's `plot_components_impl` figure from `molass/PlotUtils/DecompositionPlot.py`.

This is the first concrete incremental step on the **data object consolidation** parallel track defined in Rule 13 of `copilot-guidelines.md`:
> "Incremental steps: identify GUI paths that construct or pass `sd`, and replace them one by one with `ssd` equivalents."

---

## Context

**What `ComplementaryView` shows** (legacy, 2×3 grid):
- Left column: UV/XR decomposition drawn via `optimizer.objective_func(params, plot=True)`
- Right 4 cells: manually drawn P/C matrices from `lrf_info.matrices`

**What `plot_components_impl` shows** (library, 2×3 grid):
- [0,0]/[1,0]: UV/XR elution curves with component overlay
- [0,1]/[1,1]: UV absorbance and XR scattering spectra (P columns)
- [0,2]: Guinier plot
- [1,2]: Kratky plot
- Requires a `Decomposition` object

---

## The call chain

```
dialog.serial_data  (legacy sd)
    → DataTreatment.get_trimmed_sd()   → trimmed_sd
    → DataTreatment.get_corrected_sd() → corrected_sd
    → PeakEditor(trimmed_sd, corrected_sd, ...)
        → FullOptInput.get_dsets()     → Rg computed (legacy RgCurve in self.dsets)
        → show_complementary_view()    ← target replacement point
```

**One call site only**: `show_peak_editor_impl` in
`molass-legacy/molass_legacy/Optimizer/OptimizerUtils.py` (~line 69).

---

## Chosen approach: Option B — shallow sd → ssd incremental step

In `show_peak_editor_impl` (OptimizerUtils.py), after constructing
`treat`/`trimmed_sd`/`corrected_sd`, also construct a library `ssd` and
`Decomposition` and pass it to `PeakEditor` as an optional kwarg.

### Implementation steps

1. **Check whether `sd → ssd` conversion already exists** (first task next session).  
   Search for `SecSaxsData` constructed from `sd` or `SerialData` in molass-library and molass-legacy.

2. **Extend `show_peak_editor_impl`** (OptimizerUtils.py):
   ```python
   # After constructing treat/trimmed_sd/corrected_sd ...
   try:
       from molass.Legacy.SdAdapter import make_ssd_from_sd   # or wherever it lives
       ssd = make_ssd_from_sd(trimmed_sd, corrected_sd)
       decomposition = ssd.corrected_copy().quick_decomposition()
   except Exception:
       decomposition = None
   pe = PeakEditor(..., decomposition=decomposition)
   ```

3. **Extend `PeakEditor.__init__`** to accept `decomposition=None` and store it as `self.decomposition`.

4. **Rewrite `PeakEditor.show_complementary_view()`**:
   ```python
   if self.decomposition is not None:
       # use library plot_components_impl in a thin Tk dialog
       from molass.Peaks.ComponentsView import ComponentsView
       cv = ComponentsView(self.parent, self.decomposition)
       cv.show()
   else:
       # fall back to legacy ComplementaryView
       ...
   ```

5. **Create `molass-legacy/molass_legacy/Peaks/ComponentsView.py`**:  
   A minimal `Dialog` subclass that embeds `plot_components_impl` into a Tkinter canvas — analogous to what `ComplementaryView` does today but delegating all drawing to the library.

6. **Rg unification** (same session or follow-up):  
   Pass `rgcurve=ssd.get_rg_curve()` (library, cached) to `plot_components_impl` instead of relying on the legacy Rg thread. The legacy thread in `PeakEditor.prepare_rg_curve` is kept for now (still needed by the optimizer).

---

## Key files to touch

| File | Change |
|------|--------|
| `molass-legacy/.../Optimizer/OptimizerUtils.py` | Construct `ssd`/`Decomposition`, pass to `PeakEditor` |
| `molass-legacy/.../Peaks/PeakEditor.py` | Accept `decomposition=` kwarg, update `show_complementary_view()` |
| `molass-legacy/.../Peaks/ComponentsView.py` | New: thin Tk dialog wrapping `plot_components_impl` |
| `molass-library/molass/PlotUtils/DecompositionPlot.py` | No changes expected |

---

## Invariants to preserve

- Legacy `ComplementaryView` path remains as fallback — no existing behaviour broken
- `PeakEditor` constructor signature change is additive only (`decomposition=None` default)
- Legacy Rg computation thread (`prepare_rg_curve`) is untouched
- Both repos stay in a working state after each commit
