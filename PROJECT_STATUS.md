# Project Status — molass-library

**Last Updated**: April 29, 2026 (evening)  
**Current version**: 0.9.4

> **Conventions and architecture**: See [.github/copilot-instructions.md](.github/copilot-instructions.md)  
> **Chat session rules**: See [Copilot/copilot-guidelines.md](Copilot/copilot-guidelines.md)  
> **This document**: Tracks current development task and chronological history

---

## 🎯 Current Task

**Phase 5 dashboard complete; molass-legacy#34 fully closed; two Tkinter GUI crashes fixed ✅**  
Next: Choose next feature — candidates: Kratky preprocessing (P6+), NS in-process crash root-cause, or JOSS paper revision.

---

## 🎯 Recent Work

### April 29, 2026 — Phase 5 polish + molass-legacy#34 closed + two Tkinter GUI crashes fixed

**molass-legacy changes** (v0.5.7 → v0.6.0):

| File | Change |
|------|--------|
| `MplMonitor.py` | `_running_status()` → status label shows "(in-process)" vs "(subprocess)"; `for_run_info()` auto-detects `function_code` via `optimizer.get_function_code()` → fixes `model=None`; atexit lock-free cleanup (deadlock fix); `_RunInfoSource.terminate()` calls `request_stop()`; `_RunInfoSource.run()` added for Resume path |
| `InProcessRunner.py` | atexit + `finally` lock-free cleanup of `fileh` — same deadlock fix as MplMonitor |
| `ModeledPeaks.py` | `from molass_legacy.UV.UvPreRecog import UvPreRecog` moved before the `baseline_type` branch; was only imported in `== 1` branch but used unconditionally → `UnboundLocalError` in the Tkinter GUI when `baseline_type == 2` or `3` |
| `UvBaseSpline.py` | Added `if ty is not None:` guard in `__call__()` before `np.cumsum(ty)`; `get_curve_xy_impl()` passes `ty = None` (dummy) → `float * array(None)` → `TypeError` |
| `BackRunner.py` | Saves `in_folder.txt` to job folder (enables `DsetsDebug.reconstruct_subprocess_dsets()`) |
| `OptimizerMain.py` | Injects parent's exported `uv_diff_spline_x/y.npy` into subprocess optimizer (molass-legacy#34 final fix) |
| `OptimizerSettings.py` | Added `trust_rg_curve_folder` setting (set `True` by parent when rg-curve exported) |
| `DsetsDebug.py` *(new)* | Debug tool: reconstructs subprocess datasets for parity comparison |
| `pyproject.toml` | `0.5.7` → `0.6.0` |

**molass-library changes** (molass_legacy dep bumped to `>=0.6.0`):

| File | Change |
|------|--------|
| `LegacyBridgeUtils.py` | `prepare_rigorous_folders()` exports parent's `uv_diff_spline_x/y.npy` and sets `trust_rg_curve_folder=True` |
| `RunInfo.py` | `request_stop()` method; `compare_subprocess_dsets()` debug tool; `_stop_event` attribute |
| `RigorousImplement.py` | Passes `stop_event` to `run_optimizer_in_process()` |
| `Decomposition.py` | Minor fix |
| `pyproject.toml` | `molass_legacy>=0.5.6` → `>=0.6.0` |

**molass-legacy#34 closing verified** (April 29):  
Final divergence source was `uv_curve.spline` built with 0-based x in subprocess vs original frame numbers in parent. Fixed in `BasicOptimizer.__init__` (commit `5845cd8`). SV=78.23 vs parent 78.24 (delta_fv=0.0003). Issue closed.

**Atexit deadlock root cause** (kernel restart hang):  
`_fh.close()` in atexit acquires the handler lock. The daemon optimizer thread holds the same lock during log calls → deadlock when Python atexit runs `_fh.close()` concurrently. Fix: remove `_fh` from `_handlerList` (no lock needed) + `_fh.stream.close()` (no lock) — `logging.shutdown()` never sees the handler and the stream is closed safely.

**13u_ns_subprocess_monitoring.ipynb**: Cell [5] now has `progress=None` — `progress='dashboard'` raises `ValueError` when `in_process=False`.

### April 27, 2026 — Phase 5: `progress='dashboard'` for in-process BH runs (molass-library#139)

**All fixes in molass-legacy** (3 commits on `main`, unpushed):

| commit | change |
|--------|--------|
| `b7cbf10` | `MplMonitor.for_run_info()`: add `niter` kwarg; set `self.niter/num_trials/max_trials/optimizer/dsets/job_state=None/curr_index`; guard `update_plot()` with `if job_state is None: return`; lazy `job_state` init in `watch_progress()` once `run_info.work_folder` is populated |
| `e96da26` | `RigorousImplement.py`: pass `niter=niter` to `MplMonitor.for_run_info()` |
| `d97b732` | `InProcessRunner.run_in_process_impl()`: explicitly remove `Logger` handlers from root logger in `finally` block — **fixes kernel-restart hang** |

**Root cause of kernel-restart hang** (found this session):  
`Logger("optimizer.log")` inside the optimizer daemon thread adds a `StreamHandler(sys.stderr)` to the **root logger**. In Jupyter, `sys.stderr` is ipykernel's `OutStream`. Python's `logging.shutdown()` atexit handler flushes all root-logger handlers on process exit. Flushing `OutStream` while the asyncio event loop is shutting down deadlocks the event loop, preventing kernel restart from completing.  
Fix: `finally` block now removes both the `FileHandler` and `StreamHandler` from the root logger immediately after `solve()` returns.

**Bug fixed in MplMonitor** (same session):  
`for_run_info()` never called `run_impl()`, so `job_state`, `niter`, `optimizer`, `dsets` etc. were all absent. `show()` → `update_plot()` crashed with `AttributeError: 'MplMonitor' object has no attribute 'job_state'`. Fixed by setting required attributes in `for_run_info()` and guarding `update_plot()`.

**Tests**: 14/14 MplMonitor tests pass (test_terminate_race.py + test_mpl_monitor_dashboard.py); 5/5 progress_dashboard validation tests pass.

**Status**: molass-legacy commits are local only (not pushed). Kernel hang prevents live test of notebook 13u — will verify after kernel kill/restart.


**Phase 3 validation** (13h notebook, NITER_CMP=20, second independent run confirmed):
- subprocess: best_fv=−1.4234, SV=78.85, wall=2448 s
- in-process: best_fv=−1.4043, SV=78.31, wall=2910 s
- `assert_parity(fv_rtol=5e-2, sv_atol=2.0, rg_atol=1.0)`: **PASS**

**Phase 4 changes**:
- `RigorousImplement.py`: `in_process=False` → `in_process=True` (default flipped)
- Convention 9 in `.github/copilot-instructions.md`: replaced old "parent vs subprocess" paragraph with split-architecture table; added `in_process=True` as the default path
- Issues #117 and #119: closed (divergence no longer reachable on default path)
- Version bump: 0.9.3 → 0.9.4

### April 26, 2026 — Run observability Tier-1 closeout + Phase 3 validation confirmed (Exp 13h)

**Commits**: `798761e`, `8c4fede`, `18f0439`

**`molass/Rigorous/RunInfo.py`** — `RunInfo.live_status()` (issue #133, closes):
- One-call dict: `{phase, n_evals, best_fv, best_sv, elapsed_s, analysis_folder, work_folder, subprocess_pid, subprocess_returncode, manifest}`
- Reads `RunRegistry` manifest + `parse_sv_history` from `callback.txt`; pure disk read, no side effects
- `work_folder` fallback: walks `analysis_folder` for `callback.txt` if attribute not set
- Phase derived from manifest `status` + `subprocess_returncode`
- Tested: running → completed → failed → unknown (4 state transitions)

**`molass/Rigorous/ComparePaths.py`** — `ComparisonResult.live_status(label=None)`:
- Convenience wrapper: returns `{label: status_dict, ...}` or single dict when `label=` given
- Composes with `aicKernelEval(expression="cmp.live_status()")` for external-observer use

**Discoverability docs** (all pushed):
- `ai-context-vscode` README: `aicKernelEval` documented (was package.json only)
- `molass-library` copilot-instructions: "Live run observability stack" subsection added under §9
- `molass-researcher` copilot-instructions: kernel-first routing rule updated — `live_status()` is now the first-line probe
- `ai-context-standard` NOTEBOOK_CONVENTIONS: `aicKernelEval` added to `ai-context-vscode` tooling list
- `molass-library` API_IMPROVEMENTS: #131–#133 + RunRegistry/aicKernelEval infrastructure logged

**Phase 3 validation — confirmed (NITER_CMP=20, Apo 2-comp)**:

| metric | subprocess | in-process | delta |
|---|---:|---:|---:|
| best_fv | −1.4232 | −1.4022 | +0.021 |
| best_sv | 78.85 | 78.24 | −0.60 |
| Rg[1] (Å) | 33.40 | 33.39 | −0.01 |
| Rg[2] (Å) | 33.23 | 32.91 | −0.31 |
| wall (s) | 1146 | 1295 | +13% |

Parity assertion passed (`fv_rtol=5e-2, sv_atol=2.0, rg_atol=1.0`). Numbers reproduce the earlier Phase 3 table (same |ΔSV|=0.60, max ΔRg=0.31 Å) — in-process path behavior is stable run-to-run. Wall-time gap (+13–18%) confirmed as UltraNest/GIL overhead, not a correctness issue.

**Notebook `13h_split_architecture_validation.ipynb`** restructured for Run-All:
- Cell [6a]: `pprint(cmp.live_status())` — canonical progress probe
- DIAG-INIT cell: extracts `run_sub/run_inp/inp_summary/sub_summary` from `cmp` so legacy diagnostic cells work when `RUN_DIAGNOSTICS=True`

**Future work filed**: `freesemt/ai-context-vscode#2` — tool-availability hints + cell-completion notification (3-strikes guard; not building yet).

### April 23, 2026 — RunInfo AI-friendliness sweep (issues #123–#125)

**`molass/Rigorous/CurrentStateUtils.py`** (public API consolidation):
- `check_progress(run_info_or_folder, label=None, write_snapshot=False)` — standalone function; accepts RunInfo or path string; returns `{'label', 'n_evals', 'best_fv', 'best_sv', 'sv_last10', 'timestamp'}`; `write_snapshot=True` writes `<analysis_folder>/optimized/progress_snapshot.json`
- All 9 CurrentStateUtils functions re-exported from `molass.Rigorous.__init__` (public namespace)
- Commits: `fdf33fa` (#123), `22850bb` (#124)

**`molass/Rigorous/RunInfo.py`**:
- Added class-level docstring listing all attributes (`ssd`, `optimizer`, `dsets`, `init_params`, `monitor`, `analysis_folder`, `decomposition`, `work_folder`, `in_process_result`)
- `work_folder` and `in_process_result` are now proper `__init__` parameters (default `None`) — no more monkey-patching
- New methods: `check_progress()`, `load_progress_snapshot()`, `load_monitor_snapshot()`
- New properties: `monitor_snapshot_json_path`, `progress_snapshot_json_path`
- Commit: `97d927f` (#125)

**`molass/Rigorous/RigorousImplement.py`**:
- Removed `run_info.work_folder = work_folder` and `run_info.in_process_result = result` monkey-patches; passed in `RunInfo(...)` constructor instead
- Commit: `97d927f` (#125)

**Tests**: 20/20 in `tests/specific/test_plot_convergence.py` pass (commit `b0f9f5a`). Issues #123, #124, #125 filed and closed.

### April 21, 2026 — Fast analytical moments for SDM lognormal init (issue #113)

- `SEC/Models/LognormalPore.py`: `sdm_lognormal_model_moments(rg, N, T, N0, t0, k, mu, sigma, me, mp)` — 64-pt Gauss-Legendre + hand-rolled `_lognorm_pdf_fast` (~50 µs/call, 200× faster than full PDF, 6× faster than scipy.stats)
- `SEC/Models/SdmEstimator.py`: `refine_lognormal_params_by_moments()` — L-BFGS-B refinement of (t0, k, mu, sigma) against per-component empirical (M1, Var) from EGH ccurves
- Wired into `estimate_sdm_lognormal_from_monopore()` via `decomposition=` + `moment_refine=True` kwargs (default on)
- `SEC/Models/SDM.py`: passes `decomposition=decomposition` so default lognormal pipeline benefits
- `tests/specific/200_Rigorous/test_030_sdm_lognormal_moments.py`: 4 tests, all pass
- **Bug fixed during testing**: variance formula `k·I2` → `k·(k+1)·I2` (compound-Poisson 2nd raw moment of per-pore Gamma); now M1 matches FFT to 1e-8, Var to ~2%
- Issue #113 closed; commit `f0f7b62`

### April 17, 2026 — G1300 load-path + score-breakdown fixes
- `ComponentUtils.py`: `getattr(optimizer, 'function_code', None)` → `optimizer.get_function_code()` — fixed G1300 load path (#104)
- `RunInfo.py`: `get_score_breakdown()` temporarily sets `basic_floor=None` to avoid inflated fv (#103)

### April 16, 2026 — G1300 (SDM lognormal) objective wired end-to-end
- G1300 legacy objective function created (`molass-legacy/ObjectiveFunctions/G1300.py`)
- `FunctionCodeUtils.py`: activated `('lognormal', 'gamma'): 'G1300'`
- `RigorousSdmParams.py`: lognormal branch with 8-element sdmcol_params
- `ComponentUtils.py`: G1300 load path → `SdmColumn(pore_dist='lognormal')`
- `SdmParams.py`: parameter names for 8-param case
- `OptimizerUtils.py`: `"G1300": "SDM(lognormal)"` in MODEL_NAME_DICT
- GitHub issues #93 (speedup) and #94 (G1300) filed and closed

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
