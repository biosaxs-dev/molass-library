# Project Status — molass-library

**Last Updated**: April 6, 2026  
**Current version**: 0.9.1

> **Conventions and architecture**: See [.github/copilot-instructions.md](.github/copilot-instructions.md)  
> **Chat session rules**: See [Copilot/copilot-guidelines.md](Copilot/copilot-guidelines.md)  
> **This document**: Tracks current development task and chronological history

---

## 🎯 Current Task

Working on: **EGH peeler (#72) — over-detection on hard cases needs fixing**  
Next: Improve `egh_peel` for wide-range experimental data (Range/σ > 35) — adaptive threshold or restricted peel window  
See: `molass/Peaks/EghPeeler.py`, `molass-researcher/experiments/14_component_estimation/14b_hard_cases.ipynb`  
Issues: #72 (EGH peeler)

---

## 🎯 Recent Work

### April 6, 2026 — EGH peeler implementation (#72) and issue fixes (#68-71)

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
