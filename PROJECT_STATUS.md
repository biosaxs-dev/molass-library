# Project Status — molass-library

**Last Updated**: September 25, 2026  
**Current version**: 1.1.0  
**Active branch**: `main` (JOSS review concluded Aug 30, 2026 — `dev/ongoing-work` merged; see .github/copilot-instructions.md Branching Policy)

> **Conventions and architecture**: See [.github/copilot-instructions.md](.github/copilot-instructions.md)  
> **Chat session rules**: See [Copilot/copilot-guidelines.md](Copilot/copilot-guidelines.md)  
> **This document**: Tracks current development task and chronological history

---

## 🎯 Current Task

**Issue #264 — Martin-Synge EGH seeding — root cause actually fixed (after a false start)**

**Status**: ✅ `Decompose/Proportional.py` complete and validated (2026-09-25).
`LowRank/CurveDecomposer.py`'s default (non-proportional) path deliberately deferred as a
separate follow-up (see below) -- it changes the numeric output of the most-used
`quick_decomposition()` call with no arguments at all, so it needs its own review pass.

**Important correction**: the first version of this fix (hard `(tI, N)` reparameterization
alone, posted to #264 and closed same-day) was validated only against SAMPLE5 and was
**broken for other datasets** -- SAMPLE1 fit its data at only 9% (SSE/energy=0.91,
near-delta-function sigma with tau compensating), discovered only when asked to plot the
fitted curve against the raw data rather than just checking the broadness ratio. A/B
confirmed via `git stash` that this was a real regression, not pre-existing. Two follow-up
attempts (rescaling the free parameter to `sqrt(N)`; freezing `(tI, N)` outright) each fixed
one dataset while breaking another (SAMPLE5 collapsed to duplicate components; Y17AH20N
stayed broken either way) -- see
`molass-researcher/experiments/43_martin_synge_constraint/43a_param_extraction.ipynb` for
the full trail. **Lesson for future sessions on this file**: always check absolute fit
quality (fitted-sum vs. raw data, e.g. SSE/signal-energy) against multiple real datasets,
not just one dataset's broadness ratio, before considering any change here validated.

**Final design** (two-stage, all issues resolved):
1. **Stage 1 -- exact moment match, no optimization.** Each proportional slice's own
   `(mean, std)` (from `Moment`) is used directly as the EGH seed: `mu=mean`, `sigma=std`,
   `tau=0` (no skew moment available, so tau starts at 0 rather than from a per-slice
   Nelder-Mead sub-fit that could hand Stage 2 an already-inconsistent tau). Replaces the
   old `estimate_initial_params()` (removed) with `moment_match_initial_params()`.
2. **Stage 2 -- joint fit with hard structural constraints, not soft-only penalties.**
   Shared `(tI, N)` (Martin-Synge, `molass/SEC/Models/MartinSynge.py`) still jointly fit
   with per-component `(H, tR, tau)`; `sigma_i = (tR_i - tI)/sqrt(N)` still derived, never
   independently bounded. Two penalty terms added on top of the existing `TAU_BOUND_RATIO`
   tau/sigma bound: a `tR`-order penalty (mirrors `LowRank.CurveDecomposer`'s existing
   `mean_order_penalty`, since nothing else stopped components from crossing elution order),
   and -- the actual fix for the SAMPLE1/Y17 collapse -- a **hard floor on sigma**
   (`SIGMA_MIN_FRAMES=3.0` frame-widths; penalized via `SIGMA_MIN_PENALTY_SCALE`, not
   silently clipped to `VERY_SMALL_VALUE` as before). The silent epsilon-clip was the actual
   root enabler of the collapse: it let the optimizer treat "shrink sigma to ~0, let tau do
   all the shape work" as a perfectly legal, sometimes lower-cost solution.

**Result, SSE/signal-energy (fitted sum vs. raw data), validated directly from the library**:

| dataset | before this fix | after |
|---|---|---|
| SAMPLE1 | 0.9071 (near-delta-function sigma) | **0.0218** |
| SAMPLE5 (#264's own case) | 0.0208 | 0.0365 (still excellent) |
| Y17AH20N | 0.5241 | **0.0144** |

All three now fit well with one consistent design -- no more per-dataset whack-a-mole.

**Tests**: `tests/generic/200_LRF/test_060_proportional_degenerate.py`,
`tests/tutorial/05-lrf.py` (all 13 ordered tests), `tests/tutorial/10-advanced_models.py`,
`tests/tutorial/11-rigorous_optimization.py` -- 21/21 pass.

**Design discussion** (full reasoning chain, worth re-reading before touching this area
again): chat session 2026-09-25, starting from issue #264, converging through Martin-Synge
first principles (N=(tR/sigma)**2, injection time is unmeasured and must be estimated, plate
count is a column property so sharing it across components is physically motivated, tau is a
secondary modification not co-equal with sigma), discovering and root-causing the regression,
and validating the final two-stage design in
`molass-researcher/experiments/43_martin_synge_constraint/`.

**Second correction, same day**: the "final" fix above was itself still not robust -- a
*slightly* different proportions vector on the same Y17AH20N dataset (`[6,2,1.2,0.8]`
instead of `[6,2,1,1]`) reproduced the exact same collapse (SSE/energy=0.91). Root-caused to
the ORIGINAL, still-not-fully-fixed #264 diagnosis (cumulative-area slicing gives the
smallest-proportion component a huge background-dominated slice, inflating its raw moment),
now poisoning `estimate_tI_N`'s regression into a wrong-scale `N` fallback. Two more attempts
(capping the outlier std; then also rejecting degenerate regression results) each fixed one
case while breaking another already-working one -- reverted both. Direct evaluation proved
the good, low-residual solution scores far lower on the *same* objective (confirmed: this is
a **search failure**, not a landscape/formulation problem) -- yet neither `sqrt(N)`/`log(N)`
reparameterization nor `basinhopping` (30-iter multi-start) could reliably reach it; log(N)
even broke the previously-working `[6,2,1,1]` case outright. What actually worked: a
**deterministic grid search** over `DEFAULT_N_CANDIDATES = [100, 300, 1000, 3000, 10000,
30000, 100000]` -- a full Nelder-Mead run from each, keeping the lowest-objective result.
Fixes all 4 known cases (SAMPLE1 0.0134, SAMPLE5 0.0252, Y17 `[6,2,1,1]` 0.0143, Y17
`[6,2,1.2,0.8]` 0.0191), ~5-10x cost per call (7 candidates) but **no measurable full-suite
slowdown** (235s vs 239s before -- rigorous-optimization/NS tests dominate total runtime).
`estimate_tI_N()` no longer used by `Proportional.py` (dead in this file, still exported by
`MartinSynge.py`); `num_plates` kwarg now adds an extra grid candidate instead of seeding a
single regression. Also removed now-fully-dead `scale_objective`/`result1` pre-fit stage
(confirmed via inspection it never affected the final result even before today, only an
unused debug preview).

**New, not-yet-investigated finding**: in the `[6,2,1,1]` case, two of the four requested
components converged to *identical* params (same tR/sigma/H) -- the aggregate curve fit is
still excellent (SSE/energy=0.0143) since duplicating a component just doubles its density
at one point, but semantically this is a 3-component decomposition masquerading as 4
(component collapse). Not new to this fix (a general decomposition risk), not yet
investigated for this specific case.

**Resolved, same day**: reproduced by the user in a real GUI-exported notebook session, then
fixed. Root cause: the `tR`-order penalty only forbade *negative* gaps (crossing), not
*zero* gaps (two components landing on the exact same point) -- `min(0, gap)**2` is 0
whenever `gap>=0`, so full collapse was never penalized at all. Fix: replaced with a
per-adjacent-pair **minimum-separation** penalty, `MIN_SEPARATION_RATIO=0.3` times the
smallest gap already present in Stage 1's naive (contiguous, non-overlapping) slice means --
adaptive to each dataset's own scale rather than a fixed frame count. Result: collapse
eliminated (4 distinct components, min gap 38.6) **and fit quality improved** on 2 of 4 known
cases (Y17 `[6,2,1,1]` SSE/energy 0.0143→0.0064; Y17 `[6,2,1.2,0.8]` 0.0191→0.0123),
unchanged on the other 2 (SAMPLE1, SAMPLE5). 21/21 tests still pass.

**Next steps**:
1. Post a further corrected update to #264 with the full journey (two regressions found and
   fixed after the original closing comment, plus the component-collapse fix) -- the
   previous "corrected" comment claimed more robustness than it actually had.
2. Apply the same design to `LowRank/CurveDecomposer.py`'s default (peak-recognition) path,
   which has the same anti-pattern (separate, weaker, opt-in `num_plates` soft penalty,
   silent sigma epsilon-clip, no minimum-separation guard) -- larger blast radius (affects
   every un-parameterized `quick_decomposition()` call), needs its own test-suite pass
   before changing the default.

---

## 🎯 Prior Task

**xr_ranks propagation through the GUI pipeline (molass-gui rank-2 support) — complete**


**Status**: ✅ Complete (2026-09-24).

**What was done**: `Decomposition.update_xr_ranks()` (rank-2/Bounded LRF, issue #276
above) was previously only usable ad hoc, post-hoc on an already-loaded rigorous
result — setting it earlier in the pipeline (quick/upgraded decomposition) never
survived to a later reload. Three small propagation fixes, so a rank choice made
once in molass-gui's QuickView carries through automatically:
- `Decomposition.copy_with_new_components()` (used by `upgrade()`) now forwards
  `xr_ranks` the same way it already forwards `_rgcurve`.
- `CurrentStateUtils.load_rigorous_result()` gained an explicit `xr_ranks=` override
  param; falls back to `decomp.xr_ranks` when not given, so a value already on the
  passed-in `decomp` carries through to the freshly-reconstructed result.
- `RecipeRunner.rebuild_decomposition_from_recipe()` applies `recipe['xr_ranks']`
  if present, so it survives a restart/"Open Existing Analysis" reload too.

molass-gui side (separate repo, same session): QuickView gained an optional "Ranks"
entry + Apply button (blank by default, never touches `xr_ranks` unless used);
RigorousView gained a "Set Ranks…" override dialog for the post-hoc/discovery-driven
case (matches the original notebook workflow); both propagate into
`pipeline_recipe['xr_ranks']`/`recipe.json` and into exported notebooks.

**Unrelated but found+fixed in the same session**: a real `Tcl_AsyncDelete` crash in
molass-gui, root-caused to `plt.close()` alone not guaranteeing Tk teardown happens
on the main thread (reference cycles + deferred GC) — fixed with `gc.collect()`
right after, same pattern as molass-legacy's `OurTkinter.py::Dialog.destroy()`. See
[biosaxs-dev/molass-gui#4](https://github.com/biosaxs-dev/molass-gui/issues/4).

**Next steps**: none pending.

---

## 🎯 Prior Task

**Issue #276 — `update_xr_ranks()` cache-invalidation bug — fixed**

**Status**: ✅ Complete (2026-09-18).

**What was done**: Found while doing interactive rank-2 (Bounded LRF /
interparticle-effect) diagnostics on a real dataset in
`molass-researcher/experiments/42_analysis027_component4_rank2/42a_component4_guinier_check.ipynb`.
`Decomposition.update_xr_ranks()` only set `self.xr_ranks`; it never reset
`self.guinier_objects` / `self.bounded_lrf_info` / `self._shape_analysis`. Both
`get_guinier_objects()` and `get_xr_matrices()`'s Bounded LRF path guard on
`self.guinier_objects is None`, so calling `get_guinier_objects()` (an
innocuous, commonly-used accessor) *before* `update_xr_ranks()` silently left
stale, wrong-rank Rg values as the Bounded LRF fit seed — reproduced
concretely: two call orders on the same analysis-027 restore gave different
fitted `K`/`L`/`R` and provably different corrected `P` columns
(`np.allclose` → `False`), with no error or warning either way.

**Fix**: `update_xr_ranks()` now resets `self.guinier_objects = None`,
`self.bounded_lrf_info = None`, and `self._shape_analysis = None` whenever
ranks are set. Regression test added
(`tests/generic/210_Ranks/test_020_update_xr_ranks.py::test_update_xr_ranks_invalidates_cached_guinier_state`).
Verified: both call orders now produce identical `bounded_lrf_info` and
identical corrected `P` columns. Commit `f017c47`, issue closed.

**Follow-up (issue #277, same session)**: three smaller AI-friendliness items
found while fixing #276, all fixed together:
- `BoundedLrfInfo(dict)` subclass — concise `repr()` (K/L/R/Rg + array shapes
  only) instead of dumping the full `bq_bounds`/`bq_original`/`bq_coerced`
  arrays; fully backward-compatible (`info[k]['K']`, `.items()`, etc. unchanged).
- `update_xr_ranks()` docstring now states explicitly that it has no effect
  on `optimize_rigorously()`'s live search (rank/Bounded-LRF-blind internal
  engine — only the initial seed benefits).
- New `Decomposition.export_xr_components(folder)` — `molass_gui`'s
  `export_component_data()` now delegates to it instead of duplicating the
  `np.savetxt` loop.

Commits `10532e1` (molass-library), `8626b02` (molass-gui). 4 new tests, all
passing. Issue closed.

**Next steps**: none pending.

---

## 🎯 Prior Task

**Kratky-plot shape-match diagnostic (`molass/Kratky/`) — new feature, complete**

**Status**: ✅ Complete (2026-09-18).

**What was done**: New `molass/Kratky/` package providing a relative shape-match-score
heatmap for Kratky-plot analysis, replacing the unreliable `molass-legacy`
`Kratky_smoothness` score investigated in `molass-researcher/experiments/41_smoothing_kratky_plot/`.

- `FormFactors.py` — Pedersen (1997) form factors only (sphere, ellipsoid, cylinder,
  Gaussian chain).
- `ShapeLibrary.py` — single source of truth (`get_model_shapes()`, 6 `ShapeSpec` entries)
  shared by both scoring and icon rendering, so they can never drift out of column-order
  sync.
- `ShapeAnalysis.py` — peak finding (`kratky_peak_qrg`), qualitative classification
  (`classify_shape_category`), relative match scoring (`compute_shape_match_scores`), and
  `plot_shape_analysis()` (heatmap + optional column-aligned 3D shape-key row via a shared
  `n_shapes`-column `GridSpec` with a dedicated colorbar column).
- `ShapeKey.py` — cached (`lru_cache`), rasterized 3D icon strip (one icon per shape,
  no per-icon titles — redundant with the heatmap's xticklabels).
- `Decomposition.get_lrf_residual()`, `get_shape_analysis()`, `plot_shape_analysis()` —
  new public API, cached per-instance.
- Tests: `tests/specific/920_Kratky/test_010_ShapeAnalysis.py` (7 tests, all passing).
- Consumed by `molass-gui`'s new "Shape Analysis…" button (`rigorous_view.py`,
  `shape_analysis_dialog.py`) — confirmed working by the user against a real
  analysis folder.

**Next steps**: none pending for this feature.

---

## 🎯 Prior Task

**Issue #264 (proportional EGH decomposition broadness) — opt-in mitigation implemented, issue re-scoped and left open**

**Status**: ✅ This task complete (2026-09-17). Root cause (inflated per-slice moment `std`
used as sigma bound ceiling) still unaddressed — see issue for the 3 unimplemented
candidate directions.

**What was done**: `Decompose/Proportional.py` gained (1) always-on `TAU_BOUND_RATIO=0.65`
(fixes tau/sigma asymmetry, unrelated to #264's broadness) and (2) opt-in
`use_plate_penalty=False` — Martin-Synge plate-count self-consistency, threaded through
`QuickImplement.py` and `quick_decomposition(proportions=..., use_plate_penalty=True,
num_plates=14400)`. Tested on 4 real datasets: helps SAMPLE5 (#264's case: broadness ratio
~3.9x→2.73x) and EcoCas3, hurts Y17AH20N's 3-component case — kept opt-in, not default.
Full writeup: comment on [molass-library#264](https://github.com/biosaxs-dev/molass-library/issues/264),
and `/memories/repo/plate-consistency-penalty-issue-264.md` (molass-researcher machine).

**Next steps**: pick one of #264's original candidate fixes (restrict moment window /
shared-width bound / weighted moment) to address the root cause directly.

---

## 🎯 Prior Task (superseded/stale — branch reference outdated, may already be resolved)

**AI-friendliness: preserve `_rgcurve` in `copy_with_new_components()` — in progress** (branch `dev/ongoing-work`)

**Problem**: `upgrade()` causes redundant Rg curve computation (5× for 5-model comparison notebook). Root cause: `copy_with_new_components()` creates a fresh `Decomposition` object without transferring cached `_rgcurve` attribute.

**Solution implemented**: Added `_rgcurve` preservation in `molass/LowRank/Decomposition.py::copy_with_new_components()`:
```python
if hasattr(self, '_rgcurve') and self._rgcurve is not None:
    new_decomp._rgcurve = self._rgcurve
```

**Commit**: `f0e8f6e` — "AI-friendliness: preserve _rgcurve in copy_with_new_components"

**Testing**: Notebook `molass-researcher/experiments/29_five_model_approach/29a_sample1_five_models.ipynb` ready to test. After kernel restart, verify that all 5 model upgrades reuse the same cached `rgcurve` object.

**Next steps**: 
1. Test the fix in notebook
2. If successful, continue with five-model comparison experiment
3. Consider opening formal issue (#168) for expensive-object caching pattern documentation

---

## 🎯 Recent Work

### September 16, 2026 (AI-friendliness follow-through) — 8 issues filed and closed same-day (molass-legacy #99-#101, molass-library #267-269, #272-273)

Assessed AI-friendliness friction from the Guinier `RgEstimator` investigation (molass-researcher
#38) plus three pending items from the Sept 14 EcoCas3/Plk1 triage, filed GitHub issues for all of
them, and fixed all 8 in the same session:

- **molass-legacy#99/#101** (documentation-only): named the previously-unnamed "stop after 4
  candidates" throttle in `evaluate_interval` as `MAX_INTERVAL_CANDIDATES`, and added docstrings
  to `make_cadidate_pairs`/`evaluate_interval`/`guinier_interval` explaining the two-tier
  `wide_allow` vs `qrg_allow` leniency scheme.
- **molass-legacy#100**: `evaluate_interval`/`guinier_interval` now accept `max_candidates`
  (default preserves exact prior behavior). `RgEstimator._try_relaxed_legacy` (from the #38d fix
  earlier today) now calls `guinier_interval(max_candidates=None)` directly instead of maintaining
  a ~40-line verbatim duplicate of the sweep logic that would have silently drifted out of sync.
- **molass-library#269**: `RgEstimator.__init__` now guarantees `guinier_start`/`guinier_stop`
  exist as `None` sentinels even when every fallback stage fails (`SimpleGuinier`'s own
  null-result path never assigned them at all). `PlotUtils/DecompositionPlot.py::make_guinier_plot`
  now checks `sg.guinier_start is None` explicitly instead of relying on a caught `AttributeError`.
- **molass-library#272**: `RgCurveUtils.compute_rgcurve_info()`/`compute_rg_curve_from_arrays()`
  now construct `RgEstimator` instead of bare `SimpleGuinier`. Verified end-to-end on the real
  `Y17AH20N` dataset via `SecSaxsData.get_rg_curve()`: 8/1233 `NaN` frames → 0/1233.
- **molass-library#273**: `component_quality_scores()` now hard-gates on `RgEstimator.saturated`
  (a saturated fallback Rg is a finite clipped number, not `nan`, so the old `isnan`-only gate
  missed it) and discounts non-`'legacy'`/`'legacy_relaxed'` `rg_source` values via a fixed
  confidence factor, read best-effort from `decomp.get_guinier_objects()` (falls back to unchanged
  behavior if unavailable — verified safe against the existing mock-based test).
- **molass-library#268**: `Decompose/Partner.py`'s degenerate-component (near-zero `xr_h`)
  fallback now logs the component index via `logger.debug(...)`.
- **molass-library#267**: new `MappingInfo.plot_diagnostics()` — one call renders XR curve, UV
  curve, and an overlay (UV mapped onto the XR frame axis) with all peaks numbered, so a mismatch
  like the EcoCas3 case is visible without importing internal `estimate_mapping_impl(debug=True)`.

**Testing**: `tests/generic/200_LRF/test_030_get_rgs.py`, `tests/generic/010_DataObjects/test_010_SSD.py`,
`tests/tutorial/05-lrf.py` (13 tests), and the full `tests/tutorial/ -m "not slow"` suite (63 tests)
all pass. `MappingInfo.plot_diagnostics()` smoke-tested on `SAMPLE1`.

### September 16, 2026 (yet later) — relaxed-legacy retry stage: fixes window-selection bias, not just qRg strictness (molass-researcher #38d)

**Problem found while investigating the 7 large-particle frames recovered via DENSS** (`38d_relaxed_simpleguinier.ipynb`):
even a *successful* DENSS recovery (`score` capped at 0.5) can pick a materially worse Rg than a
window `SimpleGuinier` itself would have scored higher, if only it had been allowed to see it.
Traced to two independent, compounding causes:
1. The base `qrg_limit=1.3` genuinely excludes these frames — even the better candidate windows
   have `qRg` in 1.4–1.8, confirming 38b/38c's original finding.
2. **New**: `SimpleGuinier.evaluate_interval`'s "stop after the first 4 valid candidates" search
   throttle can end a per-`start` sweep before it ever reaches a shorter, better-scoring window —
   not a scoring-formula defect (`evaluate_guinier_interval` already ranks the better window
   higher whenever both are actually evaluated), but a search limitation. Traced exactly for one
   real frame: the sweep tried stops 26, 25, 24, 23 (in that order, decreasing from the widest
   qRg-valid stop) then broke, never reaching a `stop` 12 steps further down where the far
   better-scoring window lived.

**Fix implemented** in `molass/Guinier/RgEstimator.py`: a new `_try_relaxed_legacy()` stage,
inserted between the strict legacy pass and the DENSS fallback. It monkeypatches the *same*
`SimpleGuinier` instance's `evaluate_interval` with `_unthrottled_evaluate_interval` (a verbatim
copy with only the 4-candidate break removed) and retries `guinier_interval(qrg_limit=1.8)` in
place — no new dependency, no change to `molass-legacy`. Accepted only if it also clears both
failure checks (`Rg>0` and `score>0`); new `rg_source='legacy_relaxed'` value.

Validated on the full 1233-frame `Y17AH20N` dataset before implementing: 5/7 previously-DENSS-recovered
frames improved to a Rg consistent with an independently-decomposed component's Rg (e.g.
86.9→135.1 Å, 92.7→109.2 Å), 2/7 unchanged (no regression), all 3 known spurious-noise frames
(152, 343, 932) bit-for-bit unchanged, and zero frames outside the narrow retry trigger were
touched anywhere in the dataset. Re-verified against the actual implemented class: all 7 frames
now resolve via `rg_source='legacy_relaxed'` with scores ≈0.99–1.0 (vs. DENSS's capped 0.5).
Existing test suite (`tests/generic/200_LRF/test_030_get_rgs.py`,
`tests/generic/010_DataObjects/test_010_SSD.py`, 31 tests) passes unchanged.

**Still open**: same deferred items as below (`SimpleGuinier` upstream fix, `Sasrec`/peak-method
debugging, wiring `rg_source`/`score` into `component_quality_scores()`/`diagnose()`, and using
`RgEstimator` in `RgCurveUtils`'s whole-elution curve computation).

### September 16, 2026 — Guinier `RgEstimator` fallback chain + saturation flag (issue [#274](https://github.com/biosaxs-dev/molass-library/issues/274), filed retroactively, from molass-researcher #38)

**Problem** (fully investigated in `molass-researcher/experiments/38_guinier_analysis/`,
notebooks 38a/38b): legacy `SimpleGuinier` rejects any candidate window with qRg>1.3 with zero
tolerance once `basic_quality>0.5`. For large particles whose q-range naturally has few usable
low-q points, this rejects fits that are actually about as good as achievable (confirmed by a
Feigin & Svergun 1987 literature review and a from-scratch bias/variance Monte Carlo study on
both smoothed and raw experimental noise — see 38b). The old fallback (`SimpleFallback`) then
silently clipped the result to its hard-coded `MAX_RG=100`, producing a misleading Rg with no
indication it was a saturation artifact.

**Fix implemented** in `molass/Guinier/RgEstimator.py` and `SimpleFallback.py`:
1. `RgEstimator` now tries, in order: legacy `SimpleGuinier` → DENSS's `calc_rg_I0_by_guinier`
   (already vendored in `molass/SAXS/denss/core.py`, no qRg check) → `SimpleFallback` (clipped
   heuristic, last resort).
2. New `RgEstimator.rg_source` attribute (`'legacy'` / `'denss'` / `'fallback'`).
3. New `RgEstimator.saturated` attribute — True only when `rg_source=='fallback'` and the
   returned Rg sits exactly at `SimpleFallback`'s clip boundary. `estimate_rg_simply()` in
   `SimpleFallback.py` now returns a `'saturated'` key accordingly.

Verified on the motivating case (`analysis-013` component 1): Rg went from a clipped, misleading
`100.0` to a physically plausible `129.99` (`rg_source='denss'`), while an unrelated
already-working component was unaffected (`rg_source='legacy'`, same Rg as before). Existing
tests (`tests/generic/200_LRF/test_030_get_rgs.py`, `tests/generic/010_DataObjects/test_010_SSD.py`)
pass unchanged.

**Future improvement possibilities (not yet implemented, deferred from the same investigation)**:
- Give `SimpleGuinier` itself a graceful-degradation path (relax `qrg_allow` up to ~1.8–2.0 when
  no strict candidate exists, tagging the result's confidence) instead of only patching around it
  in `RgEstimator`. Bigger change — touches legacy code "tuned against many real datasets" — needs
  careful regression testing before attempting.
- DENSS's `calc_rg_by_guinier_peak` (Kratky-peak method) and `Sasrec` (regularized indirect
  Fourier transform / GNOM-equivalent, already vendored) both failed out-of-the-box on real
  exported component curves in the 38b investigation (implausible ~5 Å peak-method result;
  `Sasrec` diverged, likely due to `alpha=0` hardcoded in `estimate_dmax` and/or a mismatch
  between the optimizer's propagated error column and what `Sasrec`'s regularized fit expects).
  Worth its own debugging notebook — `Sasrec` is the theoretically "correct" long-term answer
  per the literature review, but isn't trustworthy yet on this kind of data.
- Surface `rg_source`/`saturated` through `component_quality_scores()`/`diagnose()` so a
  low-confidence Rg (DENSS-lax or fallback-clipped) is visible in the optimizer's diagnostics,
  not just on the `RgEstimator` object itself.

### September 16, 2026 (later same day) — `RgEstimator.score` fix + whole-elution validation (molass-researcher #38c)

**Problem found while validating the fix above** (`molass-researcher/experiments/38_guinier_analysis/38c_rgcurve_before_after.ipynb`):
swapping `RgEstimator` for `SimpleGuinier` in the *whole-elution* Rg curve (`get_rg_curve()`,
still `SimpleGuinier`-only today — that swap itself is not yet made) recovered all 8/1233 `NaN`
frames in the real `Y17AH20N` dataset, 7 via DENSS right on the elution peak's leading shoulder
(Rg≈116–128 Å) and 1 via the fallback clip (an isolated, likely genuinely bad frame) — a clean
independent confirmation of the 38b root cause on raw data. But all 8 recovered points carried
`score=0.000`, inherited from the failed legacy attempt — exactly the gap flagged above.

**Fix implemented**: `RgEstimator` now assigns a real, capped confidence score on both fallback
paths instead of leaving `self.score` at 0:
- `rg_source='denss'`: `score = min(_DENSS_SCORE_CAP=0.5, r_value**2)` — computed via a small
  local reimplementation of DENSS's window-shifting logic (`_guinier_fit_with_quality()`) since
  `calc_rg_I0_by_guinier()` itself only returns `(Rg, I0)`, not `r_value`.
- `rg_source='fallback'`: `score = 0.0` if `saturated` (a clipped value has no real magnitude
  information), else `min(_FALLBACK_SCORE_CAP=0.2, r_squared)` from `SimpleFallback`'s own
  `estimate_rg_simply()` result.

Re-verified on both the two-component case (component_1: `score=0.500`, component_2 unaffected
at `score=0.751`) and the full 1233-frame `Y17AH20N` re-run (7 denss frames now `score=0.500`,
the 1 saturated fallback frame correctly `score=0.000`) — cleanly distinguishing "recovered, real
answer, lower confidence" from "genuinely bad frame" by score alone.

**Still open**: wiring `rg_source`/`score` into `component_quality_scores()`/`diagnose()`, and
making `RgCurveUtils.compute_rgcurve_info()`/`compute_rg_curve_from_arrays()` use `RgEstimator`
instead of bare `SimpleGuinier` for the whole-elution curve (currently only demonstrated in the
38c notebook, not applied to the library).

### September 16, 2026 (later still) — spurious-fit-on-noise trigger (`score == 0`) fix (molass-researcher #38c)

**Problem found while eyeballing the 38c whole-elution curve for outliers**: two buffer-region
frames (343, 932 — both pure noise, no real particle, confirmed by direct plotting) stood out far
above the rest by deviation from their local neighborhood. Frame 343 failed cleanly as expected
(`Rg=0` → fallback chain → `Rg=100`, `saturated`). Frame 932 did not: legacy `SimpleGuinier`
coincidentally found a "valid" negative-slope window in 10 noise points (enabled by `qrg_allow`
*increasing* as `basic_quality`→0, meant to rescue noisy-but-real signals) and returned a
confident-looking `Rg=104.6` with `score` computed as **exactly 0.0** — bypassing the
`Rg is None or Rg == 0` fallback trigger entirely since `Rg` was nonzero.

Verified directly (before implementing anything) that routing frame 932 through the existing
fallback chain actually helps: DENSS's simpler fixed-window search does *not* find the same
coincidental dip (fails cleanly, matching frame 343), and `SimpleFallback` lands on the same
`Rg=100, saturated=True` for both frames — a consistent, honest "no signal here" answer instead
of one frame looking spuriously more confident than the other.

**Fix implemented**: `RgEstimator.__init__` now also triggers the fallback chain when
`self.score == 0` (in addition to `Rg is None or Rg == 0`). Threshold chosen as exact `0.0` (not
some small epsilon) based on measured impact on the full `Y17AH20N` dataset: only 4/1225 legacy
frames hit `score == 0` exactly, vs. 76 at `1e-3`, 264 at `0.02`, 507 at `0.1` — ordinary
low-but-real fits have *some* nonzero score, so `== 0` is narrowly targeted at genuine
coincidental-noise fits without reprocessing large numbers of legitimately-poor-but-real legacy
results. Verified: frames 343 and 932 now both converge to `Rg=100.0, score=0.0, saturated=True`;
the original component_1/component_2 case (38b) is unaffected; existing test suite (31 tests)
still passes.

### May 8, 2026 — molass-legacy#52: duplicate dashboard panel fix + ATP/MY experiment notebooks (16d–16g)

**molass-legacy changes** (v0.6.0 → v0.6.1):

| File | Change |
|------|--------|
| `MplMonitor.py` | Fix duplicate upper panel for fast datasets (ATP, MY): replaced `display(self.fig)` inside `with Output():` context with `fig.savefig()` → PNG bytes → `self.plot_output.outputs = (...)` trait assignment. IPython double-routing was the root cause: a background thread calling `display()` during active cell execution routes the message to both the cell's raw output and the Output widget simultaneously. Trait assignment bypasses IPython routing entirely. |
| `pyproject.toml` | `0.6.0` → `0.6.1` |

**molass-library changes** (issue #161):

| File | Change |
|------|--------|
| `molass/Rigorous/CurrentStateUtils.py` | `parse_sv_history_per_job(analysis_folder)` — parses all jobs' `callback.txt` files and returns `{job_id: [best_sv_at_each_accepted_step]}` dict |
| `molass/Rigorous/RunInfo.py` | `sv_history_per_job` property — live access to per-job SV history for in-process runs |
| `tests/specific/200_Rigorous/test_100_sv_history_per_job.py` | Test for `parse_sv_history_per_job` |
| `.github/copilot-instructions.md` | Added molass-legacy#52 entry |

**molass-researcher new notebooks**:

| Notebook | Purpose |
|----------|---------|
| `16d_atp_bh_inprocess.ipynb` | ATP dataset: in-process BH run |
| `16e_atp_bh_subprocess.ipynb` | ATP dataset: subprocess BH run |
| `16f_my_bh_inprocess.ipynb` | MY dataset: in-process BH run |
| `16g_my_bh_subprocess.ipynb` | MY dataset: subprocess BH run |

**Root cause of duplicate panel (molass-legacy#52)**:  
IPython double-routing: background thread `display()` during active cell execution routes to both the cell's raw output and the Output widget. Fast datasets (ATP, MY) trigger this race; slow datasets (APO) do not. Fix: render figure to PNG bytes and assign `plot_output.outputs` directly as a trait — bypasses IPython routing entirely.

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
