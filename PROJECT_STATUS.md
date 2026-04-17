# Project Status — molass-library

**Last Updated**: April 17, 2026  
**Current version**: 0.9.2

> **Conventions and architecture**: See [.github/copilot-instructions.md](.github/copilot-instructions.md)  
> **Chat session rules**: See [Copilot/copilot-guidelines.md](Copilot/copilot-guidelines.md)  
> **This document**: Tracks current development task and chronological history

---

## 🎯 Current Task

Working on: **G1300 result loading & score breakdown bugs fixed** ✅  
Next: Compare SDM-lognormal rigorous result with EGH and mono-pore SDM(gamma)  
See: `molass-researcher/experiments/13_rigorous_optimization/13r_sdm_lognormal_apo.ipynb`

**Completed (April 17)**:
- `ComponentUtils.py`: `getattr(optimizer, 'function_code', None)` → `optimizer.get_function_code()` — fixed G1300 load path (#104)
- `RunInfo.py`: `get_score_breakdown()` temporarily sets `basic_floor=None` to avoid inflated fv (#103)

**Completed (April 16)**:
- G1300 legacy objective function created (`molass-legacy/ObjectiveFunctions/G1300.py`)
- `FunctionCodeUtils.py`: activated `('lognormal', 'gamma'): 'G1300'`
- `RigorousSdmParams.py`: lognormal branch with 8-element sdmcol_params
- `ComponentUtils.py`: G1300 load path → `SdmColumn(pore_dist='lognormal')`
- `SdmParams.py`: parameter names for 8-param case
- `OptimizerUtils.py`: `"G1300": "SDM(lognormal)"` in MODEL_NAME_DICT
- GitHub issues #93 (speedup) and #94 (G1300) filed and closed

---

## 🎯 Recent Work

### April 15, 2026 — Two-axis SDM variant system (pore_dist × rt_dist)

**New files**:
- `molass/Rigorous/FunctionCodeUtils.py`: `FUNCTION_CODE_MAP` dict, `detect_function_code()` — replaces k-sniffing with explicit (pore_dist, rt_dist) → function_code lookup

**Modified files** (molass-library):
- `SEC/Models/SdmComponentCurve.py`: `SdmColumn` takes pore_dist/rt_dist; `SdmComponentCurve` dispatches PDF
- `SEC/Models/SdmOptimizer.py`: reads pore_dist/rt_dist from model_params; k bounds fixed for exponential
- `Rigorous/RigorousSdmParams.py`: 6-element params for exponential (G1100), 7-element for gamma (G1200)
- `Rigorous/ComponentUtils.py`: infers variant from function code or k value on load
- `Rigorous/RigorousImplement.py`: uses `detect_function_code()` for auto-detection
- `Rigorous/CurrentStateUtils.py`: updated for function code propagation

**Modified files** (molass-legacy):
- `Optimizer/OptimizerUtils.py`: `MODEL_NAME_DICT` G1100→"SDM(exp)", G1200→"SDM(gamma)"
- `ObjectiveFunctions/G1200.py`: SDM-Gamma objective (7 params including k_gamma)
- `Optimizer/MplMonitor.py`: minor fixes
- `ModelParams/SdmParams.py`, `SdmParamsSheet.py`, `SdmPlotUtils.py`: k parameter support

**Bug fixed**: `FUNCTION_CODE_MAP` originally mapped exponential→None, causing `construct_legacy_optimizer` to call `get_function_code("SDM")` which returned None after MODEL_NAME_DICT rename. Fixed by mapping to 'G1100' explicitly.", "oldString": "## 🎯 Current Task\n\nWorking on: **Exp 13 rigorous optimization — Apo results pending** 🔬  \nNext: Check 13b Apo rigorous results, then continue with 13c (ATP) and 13d (MY) rigorous runs.  \nSee: `molass-researcher/experiments/13_rigorous_optimization/`\n\n**Pre-correction anomaly detection — rejected and reverted (April 10)**:\n- Attempted: use `self.xr` (pre-correction) in `_resolve_neg_peak_exclude()` instead of `ssd_copy.xr` (post-correction)\n- Result: buffer noise creates 152/1445 false positive frames for MY, destroys peak and UV-XR mapping\n- Also tried: contiguous-run filter (min_run=5) — insufficient, still 152 frames\n- Reverted to post-correction detection (original behavior)\n- Updated comments in `SecSaxsData.py` documenting the rejection\n- SdProxy.py min_run filter also reverted\n- All 23 SSD tests pass\n\n**Uncommitted changes**:\n- `SecSaxsData.py`: corrected_copy() unified anomaly detection + updated comments\n- `RigorousImplement.py`: corrected_ssd parameter\n- `LegacyBridgeUtils.py`: icurve source consistency\n- `DecompositionPlot.py`: anomaly band visualization

---

## 🎯 Recent Work

### April 13, 2026 — SV conversion and convergence diagnostics

**`Rigorous/CurrentStateUtils.py`**:
- `fv_to_sv(fv)`: Converts optimizer fv to Score Visualization value (0–100 scale)
  - Formula: $SV = -200 / (1 + e^{-1.5 \cdot fv}) + 100$
  - Maps: fv=-3 → SV≈98, fv=-1 → SV≈64, fv=0 → SV=0
- `JobConvergence` namedtuple: added `best_sv` field
- `ConvergenceInfo` namedtuple: added `best_sv` field
- `plot_convergence()`: rewritten for SV y-axis (0–100), color-coded bars (red <60, orange 60–80, green >80), dashed threshold at SV=80, SV annotation on best bar
- 8 tests in `tests/specific/test_plot_convergence.py` all passing

### April 10, 2026 — Pre-correction anomaly detection rejected

**Attempted**: Change `_resolve_neg_peak_exclude()` to use pre-correction `self.xr` instead of post-correction `ssd_copy.xr`, reasoning that baseline correction absorbs anomalies making post-correction detection ineffective.

**Rejected**: Pre-correction buffer noise produces massive false positives:
- MY: 218 frames flagged (15%), reduced to 152 with min_run=5 contiguous filter
- Interpolating 152 frames destroys XR peak (flat from ~350–1350)
- UV-XR mapping becomes NaN → `plot_compact` crashes
- Proof: clean SSD without `set_anomaly_mask()` → valid mapping (slope=0.97) → plot works

**Reverted**: Both `SecSaxsData.py` and `SdProxy.py` restored to post-correction detection. Comments updated to document the rejection rationale. All 23 SSD tests pass.

### April 9, 2026 — Anomaly handling: recognition curve fix, unified detection, visualization bands

**Recognition curve consistency** (from prior session):
- `make_dsets_from_decomposition()` now uses `ssd.xr.get_icurve()` as optimizer's XR fitting target (was recognition curve)
- UV icurve also from SSD (not decomposition object) for data-state consistency

**Anomaly mask propagation**:
- `_apply_anomaly_interpolation()` now accepts `corrected_ssd=` to read cached mask (corrected data needed for auto-detection)
- `corrected_copy()` caches resolved bool mask as `ssd.xr.anomaly_mask` after detection

**Visualization bands** (`_draw_anomaly_bands` in DecompositionPlot.py):
- Reads cached anomaly mask, draws red axvspan bands on both XR and UV panels
- UV bands mapped from XR via channel mapping

**UV anomaly detection — FAILED ATTEMPT**:
- Tried `uv_icurve.y < 0` as UV anomaly criterion
- For MY at 290nm, this flags the actual absorption peak → interpolation destroys UV signal → `estimate_mapping` can't find peaks → RuntimeError
- Reverted to XR-only auto-detection. UV interpolation only from XR-mapped frames.

### April 8, 2026 — Exp 13 conformance, subprocess coordinate contract (issue #80, #81)

**EGH Peeler** (`molass/Peaks/EghPeeler.py` — NEW):
- Sequential EGH peak peeling: fit tallest → subtract → repeat
- `egh_peel(x, y, num_components=None, min_area_frac=0.02, min_sigma=3.0, debug=False)`
- Replaces legacy `recognize_peaks` (greedy subtraction) in `CurveDecomposer.py`
- All 13 tutorial/05-lrf tests pass with new peeler
- **Known issue**: Over-detects on experimental datasets (Apo→4, ATP→6, MY→8 peaks) due to wide frame range

**Issues fixed**:
- #68: `detect_peaks()` crash fix
- #69: `Recognizer.py` improvements
- #70: Trimming utilities update
- #71: `SecSaxsData`/`UvData` fixes
- #72: EGH peeler (GitHub issue created)

**Files changed**: `SecSaxsData.py`, `UvData.py`, `CoupledAdjuster.py`, `CurveDecomposer.py`, `Recognizer.py`, `SecSaxsDataPlot.py`, `TrimmingUtils.py`, `pyproject.toml`, tests

**Resume Job button** (molass-legacy MplMonitor.py):
- Replaced "Skip Job" with functional "Resume Job" button + `trigger_resume()` handler
- Buttons enabled/disabled based on job state

**Static result viewer**:
- `Decomposition.load_rigorous_result(analysis_folder, jobid=)` — loads from callback.txt without subprocess
- `for_split_only=True` in `construct_legacy_optimizer()` for lightweight parameter splitting
- `clear_jobs=False` parameter to preserve job history

**Job inspection utility** (#59):
- `Decomposition.list_rigorous_jobs(analysis_folder)` → `JobInfo(id, iterations, best_fv, timestamp)`
- Optimizer folder layout documented in `optimize_rigorously()` docstring (#58)

### March 26, 2026 — Per-component freezing in rigorous optimization

- Updated `.github/copilot-instructions.md` to AI Context Standard v0.8
- Created `.github/prompts/init.prompt.md` (`alwaysApply: true`) for automatic session initialization
- Added `.github/vscode-version.txt` (gitignored); updated ecosystem table (molass-essence, molass-technical now have context files)
- Applied across all 10 repos in the molass workspace

### March 24, 2026 — Negative-peak baseline + AI-friendliness improvements (v0.8.4–0.8.7)

Issues #46–#49 implemented and closed.

| Issue | Fix |
|-------|-----|
| #46 `get_baseline2d(endpoint_fraction=...)` | `LpmBaseline.py`, `SsMatrixData.py` — opt-in endpoint-anchored LPM for negative-peak datasets |
| #47 `E` optional in constructors | `SsMatrixData`, `XrData`, `UvData` — `E=None` default |
| #48 `corrected_copy()` forwards `**baseline_kwargs` | `SecSaxsData.py` — passes `endpoint_fraction` etc. through |
| #49 Reorder args to `(M, iv, jv, E=None)` | `SsMatrixData`, `XrData`, `UvData` — data matrix first (breaking change) |

---

All 5 issues (#8–#12) implemented and closed.

| Issue | Fix | New files |
|-------|-----|-----------|
| #8 `get_rgs()` → `nan` | `LowRank/Decomposition.py` | `tests/generic/200_LRF/test_030_get_rgs.py` |
| #9 `plot_components()` axis-injectable | `PlotUtils/DecompositionPlot.py`, `Decomposition.py` | — |
| #10 q-grid alignment | `Decomposition.py` | `LowRank/AlignDecompositions.py` |
| #11 component reliability | `Decomposition.py` | `LowRank/ComponentReliability.py` |
| #12 shape/unit docstrings | `Decomposition.py` | — |

Tutorial tests added: `test_012_align_decompositions`, `test_013_component_quality_scores` in `tests/tutorial/05-lrf.py`.  
Top-level export added: `molass.align_decompositions`.

---

### March 6, 2026 — API improvement issues filed (#8–#12)

**Trigger**: External research use in `molass-researcher` (Experiment 01: SEC-SAXS pre-averaging study) surfaced 5 API friction points.

**Issues filed**:
| Issue | Title | Severity |
|-------|-------|----------|
| [#8](https://github.com/biosaxs-dev/molass-library/issues/8) | `get_rgs()` returns `None` silently — causes runtime crashes | High | ✅ Fixed |
| [#9](https://github.com/biosaxs-dev/molass-library/issues/9) | `plot_components()` not axis-injectable | Medium | ✅ Fixed |
| [#10](https://github.com/biosaxs-dev/molass-library/issues/10) | No q-grid alignment utility | Medium | ✅ Fixed |
| [#11](https://github.com/biosaxs-dev/molass-library/issues/11) | No component reliability indicator for forced decompositions | Medium | ✅ Fixed |
| [#12](https://github.com/biosaxs-dev/molass-library/issues/12) | Missing array shape/unit docstrings | Low (human) / High (AI-assisted) | ✅ Fixed |

Full details and workarounds: [Copilot/API_IMPROVEMENTS.md](Copilot/API_IMPROVEMENTS.md)

**Status**: 🔄 Implementation in progress — #8 fixed (March 6, 2026).

---

### February 19, 2026 — P1+ diagnosis + AI-readability pass

**P1+ (overlap degradation) root cause traced**:
- Default `quick_decomposition()` path uses greedy `recognize_peaks` (from `molass-legacy`) + single Nelder-Mead
- `proportions=[1,1]` path bypasses this with cumulative-area slicing — robust to 3:1 peak mismatch
- Verified: std ≤ 0.02 (proportions) vs 0.27 (default) in overlap stress tests

**AI-readability improvements made**:
- Inline comments added at `recognize_peaks` import and call site in `CurveDecomposer.py`
- Unused fix levers (`randomize`, `global_opt` kwargs) documented in COPILOT-INIT.md
- `COPILOT-INIT.md` created for `molass-legacy` as cross-repo entry point
- `quick_decomposition()` docstring improved; tutorial pages updated

**Status**: ✅ Complete.

---

## ⏳ Next Steps

1. Update `molass-researcher` notebook (`01c_comparison_analysis.ipynb`) to use `molass.align_decompositions` and `component_quality_scores` — replacing the manual workarounds
2. Consider publishing v0.8.3 to PyPI
