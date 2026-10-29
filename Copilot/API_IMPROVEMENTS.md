# API Improvement Proposals

**Source**: Friction points identified during AI-assisted research in `molass-researcher` (Experiment 01, March 6, 2026)  
**Context**: Running MOLASS on 6 SEC-SAXS datasets in a Jupyter notebook workflow, comparing original vs pre-averaged data. The issues below caused code failures or workarounds during that work.

---

## 1. `get_rgs()` should not return `None` silently

**Current behaviour**: When Guinier fitting fails for a component (e.g. because the component is a noise artifact from forced `num_components`), `get_rgs()` returns `None` in the list for that position.

**Problem**: This silently breaks all downstream numeric code. Example crash:
```python
for rg in decomp.get_rgs():
    print(f"Rg = {rg:.2f} Å")   # TypeError if rg is None
```
The failure mode is a `TypeError` at the format string, with no contextual message about which component failed or why.

**Recommendations** (in order of preference):
- Return `float('nan')` instead of `None` — composable with numpy math, and `math.isnan(rg)` is an explicit guard
- OR raise a named exception with context: `GuinierFailedError(component=2, reason="not enough valid data points")`
- OR add a companion `get_rg_flags()` → `["ok", "failed", "failed"]` so callers can inspect quality without try/except

**Workaround used**:
```python
rg_str = f"{rg:.2f}" if rg is not None else "N/A (Guinier failed)"
```

---

## 2. `plot_components()` is not axis-injectable

**Current behaviour**: `plot_components()` always creates its own `plt.figure()` internally. Calling `plt.sca(ax)` before it has no effect.

**Problem**: Cannot be embedded in a subplot grid. Any attempt to build a multi-panel figure with `plt.subplots()` and then call `plot_components()` into a specific axis silently produces a separate floating figure (and a blank subplot).

**Recommendation**: Add optional `fig=None` / `axes=None` parameters following the standard matplotlib convention:
```python
def plot_components(self, title=None, fig=None, axes=None):
    if fig is None:
        fig, axes = plt.subplots(...)
    # draw into provided axes
```

**Workaround used**: Called `plot_components()` standalone for each dataset and saved each figure individually, rather than composing a comparison grid.

---

## 3. No q-grid alignment utility

**Current behaviour**: `get_xr_matrices()` returns `P` with shape `(n_q, n_components)`, where `n_q` differs between datasets because trimming leaves different numbers of q-points. There is no built-in way to compare P(q) profiles across datasets.

**Problem**: `scipy.stats.pearsonr(P_a, P_b)` raises a `ValueError` when the arrays have different lengths (e.g. 966 vs 963 points). This is a routine need whenever comparing two decompositions.

**Recommendation**: Add a utility to project a scattering profile onto a target q-grid:
```python
decomp.P_at(q_target)   # interpolated P(q) array at given q values
# or
molass.align_decompositions(decomp_a, decomp_b)  # returns both P arrays on common grid
```

**Workaround used**:
```python
q_common = np.linspace(max(q_a[0], q_b[0]), min(q_a[-1], q_b[-1]), 500)
P_a_interp = np.interp(q_common, q_a, P_a[:, 0])
P_b_interp = np.interp(q_common, q_b, P_b[:, 0])
r, _ = pearsonr(P_a_interp, P_b_interp)
```

---

## 4. No component reliability indicator for forced decompositions

**Current behaviour**: `quick_decomposition(num_components=N)` forces exactly N components regardless of data quality. There is no returned quality metric to distinguish real from spurious components.

**Problem**: When `num_components` is forced higher than the data supports, the extra components are noise artifacts. There is currently no programmatic way to detect this — the only signal is `get_rgs()` returning `None` (see issue 1), but even then, components with a valid Guinier fit may still be physically spurious.

**Recommendation**: Add a per-component reliability flag or score:
```python
decomp.is_component_reliable(i)   # bool
decomp.component_quality_scores() # list of floats, e.g. SNR or residual fraction
```

**Workaround used**: Manual inspection of Rg values — if all components have similar Rg (e.g. all ≈ 32 Å) the decomposition is flagged as physically implausible.

---

## 5. Return shape documentation is missing

**Current behaviour**: The docstrings for `get_xr_matrices()`, `get_xr_components()`, `get_rgs()`, `get_proportions()` do not document array shapes or units.

**Problem**: Key facts like "P has shape `(n_q, n_components)`", "C has shape `(n_components, n_frames)`", "Rg is in Ångströms" had to be discovered by inspection or trial and error during AI-assisted work. An AI assistant cannot inspect objects interactively the way a human at a REPL can, so missing docstrings have a higher cost in agentic workflows than in human-only workflows.

**Recommendation**: Add numpy-doc style docstrings with explicit shape annotations:
```python
def get_xr_matrices(self):
    """
    Returns
    -------
    M : ndarray, shape (n_q, n_frames)
        Measured scattering matrix.
    C : ndarray, shape (n_components, n_frames)
        Elution curves per component.
    P : ndarray, shape (n_q, n_components)
        Scattering profiles per component (columns).
    Pe : ndarray, shape (n_q, n_components)
        Estimated errors on P.
    """
```

---

## Summary

| # | Issue | Severity | Fix complexity |
|---|-------|----------|----------------|
| 1 | `get_rgs()` returns `None` silently | High — causes runtime crashes | Low |
| 2 | `plot_components()` not axis-injectable | Medium — forces awkward workflow | Medium |
| 3 | No q-grid alignment utility | Medium — common need, manual workaround | Low |
| 4 | No component reliability indicator | Medium — forced decompositions produce silent garbage | Medium |
| 5 | Missing shape/unit docstrings | Low (human) / High (AI-assisted) — slow to discover | Low |

---

## Follow-through After Implementation

Once the fixes above are implemented:

1. **Bump version** (0.8.2 → 0.8.3 or appropriate) before releasing, so that downstream experiment notebooks can record which molass version produced each result. This is important for reproducibility — `molass-researcher` experiment logs reference molass by version.

---

## GitHub Issue Status

**Last verified**: March 11, 2026

| # | GitHub Issue | Title | Status |
|---|-------------|-------|--------|
| — | [#15](https://github.com/biosaxs-dev/molass-library/issues/15) | Add `wavelengths` and `frames` aliases to `UvData` | ✅ Done (closed) |
| 1 | [#8](https://github.com/biosaxs-dev/molass-library/issues/8) | `get_rgs()` returns `None` silently | ✅ Done (closed) |
| 2 | [#9](https://github.com/biosaxs-dev/molass-library/issues/9) | `plot_components()` not axis-injectable | ✅ Done (closed) |
| 3 | [#10](https://github.com/biosaxs-dev/molass-library/issues/10) | No q-grid alignment utility | ✅ Done (closed) |
| 4 | [#11](https://github.com/biosaxs-dev/molass-library/issues/11) | No component reliability indicator | ✅ Done (closed) |
| 5 | [#12](https://github.com/biosaxs-dev/molass-library/issues/12) | Missing shape/unit docstrings | ✅ Done (closed) |
| — | [#13](https://github.com/biosaxs-dev/molass-library/issues/13) | ComponentCurve.y, trimmed_copy(nsigmas=), auto-mapping (v0.8.4) | ✅ Done (closed) |
| — | [#14](https://github.com/biosaxs-dev/molass-library/issues/14) | SecSaxsData non-standard data support | ✅ Done (closed) |

### Newly filed (March 10, 2026)

Discovered during Experiment 01f (March 9, 2026):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#16](https://github.com/biosaxs-dev/molass-library/issues/16) | `.data` alias for `.M` in `SsMatrixData` | ✅ Done (closed) |
| [#17](https://github.com/biosaxs-dev/molass-library/issues/17) | Informative `__repr__` for `SsMatrixData` and `UvData` | ✅ Done (closed) |
| [#18](https://github.com/biosaxs-dev/molass-library/issues/18) | Document `simple_plot_3d` ax parameter and caller responsibilities | ✅ Done (closed) |
| [#19](https://github.com/biosaxs-dev/molass-library/issues/19) | Add `uv.wavelength_range` property to `UvData` | ✅ Done (closed) |
| [#20](https://github.com/biosaxs-dev/molass-library/issues/20) | Add `decomp.get_rg_curve()` to `Decomposition` (returns `RgCurve`) | ✅ Done (closed) |

### Newly filed (March 11, 2026)

Discovered during Experiment 01g (March 2026):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#21](https://github.com/biosaxs-dev/molass-library/issues/21) | `RgCurve.x` should carry original frame numbers, not column indices | ✅ Done (closed) |
| [#22](https://github.com/biosaxs-dev/molass-library/issues/22) | `RgCurve.y` should be float array with `nan`, not object array with `None` | ✅ Done (closed) |

### Newly filed (April 23, 2026)

Discovered during Experiment 13h (rigorous optimization, UltraNest):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#123](https://github.com/biosaxs-dev/molass-library/issues/123) | Add `RunInfo.check_progress()` for mid-run progress monitoring | ✅ Done (closed) |
| [#124](https://github.com/biosaxs-dev/molass-library/issues/124) | Add `write_snapshot` to `check_progress`; add `RunInfo.load_progress_snapshot()` | ✅ Done (closed) |
| [#125](https://github.com/biosaxs-dev/molass-library/issues/125) | Document `RunInfo` attributes; add `work_folder`/`in_process_result` to constructor; remove monkey-patches | ✅ Done (closed) |

### Newly filed (April 26, 2026)

Discovered while validating Phase 3 split-architecture (in-process vs subprocess) on Experiment 13h:

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#131](https://github.com/biosaxs-dev/molass-library/issues/131) | (duplicate of #132) | ✅ Closed as dup |
| [#132](https://github.com/biosaxs-dev/molass-library/issues/132) | `work_folder` consistency between in-process and subprocess paths | ⏳ Open |
| [#133](https://github.com/biosaxs-dev/molass-library/issues/133) | `RunInfo.live_status()`: one-call progress dict for in-flight runs | ✅ Done (closed) |

Related infrastructure shipped alongside #133:

| Component | Where | Purpose |
|-----------|-------|---------|
| `RunRegistry` (`read_manifest`, `locate_recent_runs`, `write_run_manifest`, `update_run_manifest`) | `molass.Rigorous` | Disk-side `RUN_MANIFEST.json` breadcrumbs in both `analysis_folder` and `work_folder` |

### Newly filed (September 9, 2026)

Discovered while reviewing paper-1.tex (molass-papers) for a "CEDM" wording removal:

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#262](https://github.com/biosaxs-dev/molass-library/issues/262) | `ModelFactory.create_model()` only defaulted `shared_column=True` for `'cedm'`, not `'edm'`, even though the real default (in `EdmOptimizer`/`EdmEstimatorImpl`) already treats both identically — the asymmetry falsely implied the two model names still diverge in behavior | ✅ Done (closed) |

| `ComparisonResult.live_status()` | `molass.Rigorous.ComparePaths` | Convenience wrapper over the per-path `RunInfo.live_status()` |
| `aicKernelEval` tool | [ai-context-vscode](https://github.com/freesemt/ai-context-vscode) v0.3.0 | External-observer access to live kernel state — composes with `live_status()` for one-tool-call run probes |

Discovered while debugging `in_process=False` in molass-researcher experiment 16b:

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#159](https://github.com/biosaxs-dev/molass-library/issues/159) | Auto-degrade `progress='dashboard'` when `in_process=False` instead of raising `ValueError` | ✅ Done (bdb8697) |

2. **Simplify `molass-researcher` 01c workarounds** — the notebook `experiments/01_shimizu_averaging/01c_comparison_analysis.ipynb` previously contained manual workarounds for issues #1 and #3. Now that fixes are in place, consider revisiting `01c` to replace workarounds with the cleaner API calls. This is optional (the workarounds work), but it keeps the research notebook idiomatic.

### Newly filed (September 16, 2026)

Discovered during new-dataset triage (EcoCas3 / Plk1, Sept 14) and the Guinier `RgEstimator` investigation (molass-researcher #38, Sept 16):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#274](https://github.com/biosaxs-dev/molass-library/issues/274) | Guinier `RgEstimator`: large-particle qRg rejection, spurious noise fits, and window-selection bias (filed retroactively -- fix already implemented) | ✅ Done (closed) |
| [#267](https://github.com/biosaxs-dev/molass-library/issues/267) | `MappingInfo.plot_diagnostics()` — one-call XR/UV peak-matching visualization | ✅ Done (closed) |
| [#268](https://github.com/biosaxs-dev/molass-library/issues/268) | Log the degenerate-component fallback in `Decompose/Partner.py` | ✅ Done (closed) |
| [#269](https://github.com/biosaxs-dev/molass-library/issues/269) | `RgEstimator` should set explicit `None` sentinels instead of relying on `AttributeError` | ✅ Done (closed) |
| [#272](https://github.com/biosaxs-dev/molass-library/issues/272) | `RgCurveUtils` should use `RgEstimator` instead of bare `SimpleGuinier` | ✅ Done (closed) |
| [#273](https://github.com/biosaxs-dev/molass-library/issues/273) | Surface `rg_source`/`score`/`saturated` in `component_quality_scores()`/`diagnose()` | ✅ Done (closed) |
| [molass-legacy#99](https://github.com/biosaxs-dev/molass-legacy/issues/99) | Name and document `evaluate_interval`'s candidate-count search throttle | ✅ Done (closed) |
| [molass-legacy#100](https://github.com/biosaxs-dev/molass-legacy/issues/100) | Allow `evaluate_interval`'s candidate-count throttle to be parameterized | ✅ Done (closed) |
| [molass-legacy#101](https://github.com/biosaxs-dev/molass-legacy/issues/101) | Add docstrings to `make_cadidate_pairs`/`evaluate_interval`/`guinier_interval` | ✅ Done (closed) |

**#272/#273 details**: `RgCurveUtils.compute_rgcurve_info()`/`compute_rg_curve_from_arrays()` now
construct `RgEstimator` instead of bare `SimpleGuinier` — verified this recovers all 8/1233 `NaN`
frames on the real `Y17AH20N` dataset via the actual `SecSaxsData.get_rg_curve()` call (not just
a notebook replica). `component_quality_scores()` now hard-gates on `RgEstimator.saturated` (a
saturated fallback Rg is a finite number, not `nan`, so the old `isnan` gate alone missed it) and
discounts non-`'legacy'`/`'legacy_relaxed'` `rg_source` values by a fixed confidence factor
(`_RG_SOURCE_CONFIDENCE`), best-effort via `decomp.get_guinier_objects()` with a safe fallback to
unchanged behavior if unavailable.

**#100 details**: `SimpleGuinier.evaluate_interval`/`guinier_interval` (molass-legacy) now accept
`max_candidates` (default `MAX_INTERVAL_CANDIDATES=4`, preserving existing behavior exactly);
`RgEstimator._try_relaxed_legacy` calls `guinier_interval(max_candidates=None)` directly instead
of maintaining a ~40-line verbatim duplicate of the sweep logic.

### Newly filed (October 2, 2026)

Discovered while debugging a GUI-exported "restored session" notebook in `molass-researcher`
(`RunInfo.reconnect()` followed by `decomp.plot_components()` silently showing the
pre-optimization decomposition instead of the restored best result):

| GitHub Issue | Description | Status |
|-------------|-------------|--------|
| [#290](https://github.com/biosaxs-dev/molass-library/issues/290) | `RunInfo.reconnect()` leaves no documented path to a plottable, optimized `Decomposition`; `get_current_decomposition()` depends on a possibly-stale global legacy setting and disagrees with `score()` on which job is "current"; `reconnect()` docstring has a duplicate `load_best` entry | ✅ Done (closed) |
| [#314](https://github.com/biosaxs-dev/molass-library/issues/314) | Shape-match window is a module constant bound at definition time; no per-call `qrg_window` | ✅ Done (closed) |
| [#315](https://github.com/biosaxs-dev/molass-library/issues/315) | No public way to match a bare Kratky curve (`match_kratky_curve`) | ✅ Done (closed) |
| [#316](https://github.com/biosaxs-dev/molass-library/issues/316) | `kratky_descriptors` returned `None` without an interior peak; now same keys + `has_peak` | ✅ Done (closed) |
| [#317](https://github.com/biosaxs-dev/molass-library/issues/317) | Shape-match ergonomics: `ShapeMatchResult.best_shape`, relative vs raw score docs, form-factor signature table | ✅ Done (closed) |
| [#318](https://github.com/biosaxs-dev/molass-library/issues/318) | No reader for DENSS component result files (`molass.SAXS.DenssResult`) | ✅ Done (closed) |
| [#322](https://github.com/biosaxs-dev/molass-library/issues/322) | `RgCurve.i0s` / `i0_errors` next to `.rgs` (per-frame Guinier I(0)) | ✅ Done (closed) |
| [#323](https://github.com/biosaxs-dev/molass-library/issues/323) | Homogeneity composing API `molass.Homogeneity`: concentration proxies, `ProxyRatio`, flatness statistics, `independent_axes` | ✅ Done (closed) |
| [#324](https://github.com/biosaxs-dev/molass-library/issues/324) | `Flatness.curvature` / `tilt_quad` (separates a mapping error, a tilt, from a concentration effect, a curvature) | ✅ Done (closed) |
| [#325](https://github.com/biosaxs-dev/molass-library/issues/325) | Composed API `SecSaxsData.homogeneity()` with `HomogeneityResult` (summary, plot, shifted, reselect); GUI dialog follows in molass-gui | ✅ Done (closed) |
| [#327](https://github.com/biosaxs-dev/molass-library/issues/327) | Homogeneity with a given or optimized mapping: `homogeneity(mapping=...)`, `Decomposition.get_uv_mapping()` / `.homogeneity()`, `mapping_shift()` | ✅ Done (closed) |
| [#321](https://github.com/biosaxs-dev/molass-library/issues/321) | `quick_decomposition` warns when it returns fewer components than `num_components` and when a component has a non-positive/negligible area share (`warn_on_suspicious_components`) | ✅ Done (closed) |
| [#328](https://github.com/biosaxs-dev/molass-library/issues/328) | `estimate_mapping()` fits through sub-frame peak positions (`SimpleMapper.refine_peak_position`, core centroid) instead of integer apexes: simulated mapping error 0.63 → 0.05 XR frames rms; resolution documented | ✅ Done (closed) |
| [#331](https://github.com/biosaxs-dev/molass-library/issues/331) | `Mapping` gets `slope`/`intercept`/`xr_to_uv`/`uv_to_xr`; `Decomposition.estimated_mapping` / `optimized_mapping` added; `Decomposition.mapping` (the estimate) warns when the UV curves use a different, optimized mapping | ✅ Done (closed) |
| [#332](https://github.com/biosaxs-dev/molass-library/issues/332) | `RgCurve.__repr__` summarizes frame count/range, gaps, finite Rg count and I(0) availability (restored curves cover part of the frames and carry no I(0)) | ✅ Done (closed) |

### Newly filed (October 26, 2026)

AI-friendliness assessment after the homogeneity work (molass-researcher experiments 50e-50g); #331 and #332 are listed above, the rest were implemented together (October 27, 2026):

| GitHub Issue | Class | Description | Status |
|-------------|-------|-------------|--------|
| [#333](https://github.com/biosaxs-dev/molass-library/issues/333) | Naming | `MappingInfo.xr_peak_frames` / `uv_peak_frames` next to the index arrays `xr_peaks` / `uv_peaks`; index-versus-frame conventions documented in the `SsMatrixData` docstring | ✅ Done |
| [#334](https://github.com/biosaxs-dev/molass-library/issues/334) | Workflow | Second `optimize_rigorously(in_process=True)` in one process: a leftover `temp_in_folder` in the legacy settings no longer breaks it; clear `RuntimeError` when trimming info is missing and nothing was exported | ✅ Done |
| [#335](https://github.com/biosaxs-dev/molass-library/issues/335) | Naming / Workflow | `RunInfo.wait_until_done(timeout=None)` / `RunInfo.is_done`: one meaning for all run kinds | ✅ Done |
| [#336](https://github.com/biosaxs-dev/molass-library/issues/336) | Navigation | `load_best_rigorous_result(decomp, analysis_folder, ...)` and `load_rigorous_result(..., jobid='best')`, with `fv`/`sv` attached; `NoCompletedJobError` (a `FileNotFoundError`) for "no result yet"; the four molass-gui dialogs use it through `molass_gui/best_result.py` | ✅ Done |
| [#337](https://github.com/biosaxs-dev/molass-library/issues/337) | Interpretability | `MappingInfo.resolution_frames`: noise-propagated uncertainty of the mapping in XR frames (see #328) | ✅ Done |
| [#338](https://github.com/biosaxs-dev/molass-library/issues/338) | Naming | `DidYouMeanMixin`: close names and aliases in the `AttributeError` of `XrData`, `UvData`, `SecSaxsData`, `Decomposition`, `Curve`/`RgCurve` | ✅ Done |
| [#339](https://github.com/biosaxs-dev/molass-library/issues/339) | Workflow | Library log messages and progress bars go to stdout (`Global/LogSetup.py`, `Global/Tqdm.py`); stderr kept for errors; no more PowerShell `NativeCommandError` for a successful run (cf. #256) | ✅ Done |
| [#340](https://github.com/biosaxs-dev/molass-library/issues/340) | Navigation | `molass.Testing.simulate_ssd(species, uv_late, noise, seed, ...)` and `Species`, with `ssd.simulation_truth` | ✅ Done |
| [#341](https://github.com/biosaxs-dev/molass-library/issues/341) | Robustness | EDM non-finite objective: `conformance_score` returns NaN for non-finite moments (no more `DLASCL` console messages), `Edm.edm_func` skips frames before `t0`; the EDM search stall is open | 🔶 Partly done |
| [#342](https://github.com/biosaxs-dev/molass-library/issues/342) | Data trimming | Default trimming hid the interparticle correction (cut the lowest-q points): `small_angle_limit` ('extended' legacy default / 'guinier' / 'none', global option and `trimmed_copy` argument), `trimmed_copy(xr_qr=...)`, recipe records `xr_qr` (old recipes rebuild with 'guinier'), `TrimmingInfo.small_angle_limit`, GUI: angular range shown, advanced low-q trimming choice, rank-2 hint; interparticle detection threshold 0.95 | ✅ Done |
| [#343](https://github.com/biosaxs-dev/molass-library/issues/343) | Correctness | `load_analysis_session`: docstring says best result, code loads the latest job | ✅ Done |
| [#344](https://github.com/biosaxs-dev/molass-library/issues/344) | Navigation | One discoverable call to open an analysis folder (best result, SV, jobs, recipe): `molass.load_analysis(folder)` returns an `AnalysisInfo` | ✅ Done |
| [#345](https://github.com/biosaxs-dev/molass-library/issues/345) | Workflow | `RUN_MANIFEST.json` status/phase go stale: `refresh_run_manifest()` derives them from the subprocess pid and the job files (`read_manifest(refresh=True)`, `locate_recent_runs`, `live_status()`) | ✅ Done |
| [#346](https://github.com/biosaxs-dev/molass-library/issues/346) | Workflow | `live_status()`: rejected (non-finite) iterations and stalled jobs (`n_jobs`, `n_entries`, `n_nonfinite`, `stalled_jobs`; `JobInfo.n_nonfinite`); shown in the molass-gui rigorous view header | ✅ Done |
| [#347](https://github.com/biosaxs-dev/molass-library/issues/347) | Naming / defaults | `get_usable_qrange_impl(debug=True)` default; `XrComponent.icurve`/`jcurve` always `None` (and `get_jcurve()` was broken) | ✅ Done |
| [#348](https://github.com/biosaxs-dev/molass-library/issues/348) | Portability | recipe/analysis folder stores the absolute data path: `recipe.json` records `dataset`, `rebuild_decomposition_from_recipe` / `load_analysis_session` / `load_analysis` take `in_folder=`, stale bundled-sample paths resolve through `molass_data` | ✅ Done |
| [#349](https://github.com/biosaxs-dev/molass-library/issues/349) | Robustness | EDM b policy: the wrong-sign `suggest_edm_bounds_from_egh` bounds never reached the optimizer; the b policy for tailing components (b = 0 or a cap) is open | ⏳ Open |
| [#350](https://github.com/biosaxs-dev/molass-library/issues/350) | Robustness | Fronting (EGH tau < 0, EDM b < 0) allowed in the rigorous stage only for components whose quick EGH fit shows it (`FrontingPolicy`, `tau/sigma < -0.05`); `fronting='auto'/'allow'/'forbid'` on `optimize_rigorously` and `upgrade('EDM')`, recorded in `recipe.json` (`fronting`, absent = former bounds), EGH tau and EDM b bounds follow it, the quick EDM stage too; shown by `load_analysis(...).summary()` and the molass-gui rigorous view | 🔶 Done, to be confirmed on the Q1/Q2 reruns |
| [#351](https://github.com/biosaxs-dev/molass-library/issues/351) | Robustness | Rigorous BH stalls on the EDM Q1 case (a and b stuck at their lower bounds, wandering steps, best = first step of each job); DE reaches fv -1.68 against -1.38 | ⏳ Open |
| [#352](https://github.com/biosaxs-dev/molass-library/issues/352) | Performance | Fast analysis status that does not rebuild the decomposition (`load_analysis` light mode; `summary()` on a running folder took > 5 min) | ⏳ Open |
| [#353](https://github.com/biosaxs-dev/molass-library/issues/353) | Diagnostics | `AnalysisInfo.diagnose()`: best = start, no improvement over N jobs, parameters on a bound, recipe without `fronting`, non-finite fraction | ⏳ Open |
| [#354](https://github.com/biosaxs-dev/molass-library/issues/354) | Workflow | `AnalysisInfo.to_summary_dict()` / `freeze()` replacing the repo freeze script | ⏳ Open |
| [#355](https://github.com/biosaxs-dev/molass-library/issues/355) | Navigation | Component `skewness()` (negative = fronting) and a summary column | ⏳ Open |
| [#356](https://github.com/biosaxs-dev/molass-library/issues/356) | Documentation | One documented public EDM function (sign convention, b = 0 limit, c0 linearization, a*b*c_inj dependence) | ⏳ Open |
| [#357](https://github.com/biosaxs-dev/molass-library/issues/357) | Navigation | Optional `note=`/`tag=` stored in `recipe.json` so analysis folders are self-describing | ⏳ Open |

**#290 details**: root cause was discoverability, not missing functionality --
`RunInfo.restore()` + `load_best()` already correctly solve "get a plottable
Decomposition for the best completed result," but `restore()` was not exported
from `molass.Rigorous`, and `reconnect()`'s own docstring never mentioned it
exists (and its worked example would itself raise `ValueError` in practice,
since bare `reconnect()` leaves `self.decomposition = None`). Fixed: exported
`restore`; rewrote `reconnect()`'s docstring (removed a duplicate `load_best`
entry, added a correct example using `restore()`, documented the `score()`
optimizer-reattachment requirement); clearer `load_best()` error message
pointing to `restore()`; added a docstring to `get_current_decomposition()`
(previously had none) and made `construct_decomposition_from_results()` prefer
`run_info.analysis_folder` over the legacy global setting when available
(molass-library commit [b61738a](https://github.com/biosaxs-dev/molass-library/commit/b61738a)).
The true root cause of the *original* bad notebook, however, was in
`molass-gui`: `build_restore_notebook()`'s idle/completed branch manually
reattached an optimizer to a bare `reconnect()` handle to plot a `Score`
object, never producing an updated `Decomposition` -- fixed there too, using
`restore()` + `load_best()` directly
([molass-gui@7a24e68](https://github.com/biosaxs-dev/molass-gui/commit/7a24e68)).

**Workaround in the meantime**: `molass.Rigorous.CurrentStateUtils.load_rigorous_result(decomp,
analysis_folder, rgcurve=...)` — a free function, not yet a documented `RunInfo` method — builds
a correct, optimized `Decomposition` from disk and is what actually worked.
