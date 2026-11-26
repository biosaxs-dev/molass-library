# molass changelog

Newest first. This file ships inside the installed package, next to `CONTEXT.md`
(`os.path.join(os.path.dirname(molass.__file__), "CHANGELOG.md")`), so it describes the version you
have, or the next ones if you upgrade. The same text is the body of each GitHub Release.

Each version has the same headings: **Changed (behavior)** (what can make existing code or results
differ; read this first), **Added**, **Fixed**, **Requires**. Issue numbers are of
`biosaxs-dev/molass-library` unless written out.

Detect a feature instead of comparing versions: `hasattr(molass, "fork_analysis")`, or
`molass.requires("1.3.0")` (raises `ImportError` when older). Versions before 1.2.2: see the GitHub Releases.

## Unreleased

### Changed (behavior)
- **Bounded LRF no longer clips B(q) below `b1 = pi/R`** (#411). `coerce_bounds` (and so `apply_bounded_lrf` and
  `Decomposition` with `xr_ranks=[2]`) applies the envelope `1/(q*L*R)^2` only for `q >= pi/R`; below that the plain
  rank-2 A(q) and B(q) are kept. The envelope is the large-x asymptote of the hard-sphere function, not a bound at low q,
  and the interparticle correction lives at low q: when B(q) had more structure at higher q than a hard sphere of radius
  `sqrt(5/3)*Rg` (non-spherical particles, long- or short-range interactions) the old code could remove real B(q) at low q
  and add it to A(q) (Guinier Rg 38-54 Å instead of 33 Å in simulations). For hard-sphere-like data and the real SAMPLE3
  the result is unchanged (identical at low q); the high-q clipping that suppresses the noise of the rank-2 solution is
  unchanged. Returned `bq_bounds` is still the envelope at all q; only the clipping is restricted.

### Added
- **`ssd.xr.error_scale()`** (#416): the true scatter of the data in units of the stated error `xr.E`, per q region, estimated
  without any model from the fourth difference over neighbouring frames (1 = the stated error is right, 2.5 = 2.5 times too
  small). Recovers a known noise factor within a few percent; emits a `UserWarning` for regions outside 0.67-1.5
  (`warn=False` to silence). A reduced chi-square of a fit cannot give this number because a wrong model inflates it in the
  same way: on SAMPLE3 the reduced chi-square of the component-curve fit is about 6 ("errors 2.5x too small") while this
  estimate is 0.94-1.0 for q >= 0.02 (the stated errors are right).
- **`Decomposition.get_curve_fit_report()`** (#416): per q region the `s = sqrt(chi2/dof)` of the fit with the component curves
  against a free SVD fit of the same rank; `report.misfit_regions()` lists where the curves, not the stated error, are what
  does not describe the data (SAMPLE3: the EGH curve gives up to 5.6 near q = 0.035, a free rank-1 fit 1.0-1.1).

## 1.3.0 (2026-11-18)

Headline: continue an analysis in a new folder under another elution model (`molass.fork_analysis`),
the score of a loaded result equals its stored value, and the library is quiet by default.

### Changed (behavior)
- **Legacy output is hidden by default** (`set_molass_options(quiet=True)` is the new default, #398).
  `upgrade`, `get_rigorous_initparams`, `get_rigorous_param_count`, `rebuild_decomposition_from_recipe`,
  `try_fast_rg_curve` and the rigorous setup discard the printed output of the legacy code. To see it: `debug=True`
  on the call, or `set_molass_options(quiet=False)`. A failing call carries the last lines of what was hidden as a note on
  its exception (`__notes__`). Warnings meant for the user (molass's own `UserWarning`) are still shown.
- **`Decomposition.score()` of a result loaded from a rigorous job evaluates the job's stored parameters** (#394),
  so `score().fv` agrees with `result.fv` (on Q4: -1.5403 instead of -1.4524). `use_stored_params=False` gives the
  old behavior (the parameters derived from the loaded curves); stored parameters of the wrong length raise `ValueError`.
- **Warnings raised in the rigorous setup are no longer swallowed** (#404): code that ran silently may now show a
  `UserWarning` (for instance the Pattern A notice of `score()` on corrected data). Numerical `RuntimeWarning` /
  `OptimizeWarning` of the legacy code stay hidden.
- `optimize_rigorously(num_jobs>1, seed_params=...)`: only round 0 starts from the seed; later rounds continue from the best
  parameters (before they restarted from the seed) (#396).
- `importlib.reload` of molass modules happens only with `debug=True` (#402). Monkeypatches in tests and notebooks now survive.
- Progress bars are off by default when the output is not a terminal (#388).
- Simulated `Sample4Like` data (`molass.Testing.simulate_sample4_like`) take their noise from the Sedlak (2017) error
  model instead of measured-error tables, so the generated data differ from 1.2.4 (#391).

### Added
- `molass.fork_analysis(source_folder, new_folder, model=None, seed='auto', match_curves=False, dry_run=False, ...)`
  continues an analysis in a new folder, under another model (`'sdm'`, `'edm'`, `'lkm'`, `'grm'`) or the same one, seeded
  from the best result (#396). `recipe.json` of the new folder records `forked_from`, `seeded_from`, `seed_params`.
  `dry_run=True` returns a `ForkPlan` (`launch()`, `score()`) without starting anything; `fork_source()` and `info=` fork from a
  decomposition you already hold without rebuilding it.
  ```python
  run = molass.fork_analysis("Q4/analysis-EGH", "Q4/analysis-GRM", model="grm", match_curves=True,
                             async_=True, monitor=False)
  molass.analysis_status("Q4/analysis-GRM").start_fv      # the objective value of the seed
  ```
- `Decomposition.upgrade(model, match_curves=True)` (GRM, LKM) fits the new components to the source curves so the new
  model starts near the source solution; the docstring now says what `upgrade()` carries over and what it does not (#395).
- `JobInfo.first_fv`, `AnalysisStatus.start_fv`, `seconds_per_callback`; the run manifest (`RUN_MANIFEST.json`) is kept current
  from inside the optimizer subprocess and its phase advances to `optimizing`; `live_status()` shows the progress (#397).
- `progress_cb(stage, fraction)` on `rebuild_decomposition_from_recipe`, `load_analysis`, `load_analysis_session`,
  `plan_fork`, `fork_analysis`: loading takes minutes on large data (#401). `molass.analysis_status(folder)` and
  `load_analysis(folder, light=True)` read the folder in seconds without the rebuild.
- `SecSaxsData.start_rg_curve_process()`: the Rg curve in a child process with live progress, no GIL competition with a GUI
  thread (#400); `molass.Global.ArrayBundle` and `XrData` / `RgCurve` `to_bundle` / `from_bundle`: named arrays for
  another process over pickle, disk or shared memory (#399).
- `Decomposition.get_residuals()`, `get_residual_report()`: residual against the measured data with Durbin-Watson and
  Shannon-limited AIC (#392).
- `molass.SAXS.ErrorModel.sedlak_sigma`, `add_sedlak_noise` (#390); `molass.Testing.simulate_tiny` for the whole chain in
  seconds (#387); did-you-mean hints on `XrComponent` / `UvComponent` (`get_rg` -> `compute_rg`, ...) (#385).
- `molass.Global.Quiet.quiet_legacy(debug)` and the thread-safety notes of `score()`, `load_rigorous_result`, `get_rg_curve()`
  (#403): `score()` builds an optimizer through code that touches matplotlib and must run on the main thread of a GUI
  application; `get_rg_curve()` may run on a worker thread or in a child process.
- `MOLASS_SETTINGS_NAME` (environment variable) keeps parallel runs from sharing a settings folder (needs molass_legacy 1.7.3) (#393).

### Fixed
- Trimming keeps all q-points when no wide-angle limit is found instead of failing (#387).
- `update_run_manifest` no longer wipes a manifest that it cannot read for a moment (concurrent write on Windows) (#396).

### Requires
`molass_legacy>=1.7.3`, Python 3.12 to 3.14. `molass_gui` 0.7.0 needs this version (with an older molass it hides its fork button and
computes the Rg curve in a thread, which slows the drawing meanwhile).

## 1.2.4 (2026-11-11)
- **Changed:** `quick_decomposition(ranks=[...])` is applied; before it was accepted and silently ignored; a list of the wrong
  length raises `ValueError` (#380).
- **Added:** `get_confirmed_peaks()` and `recommend_decomposition_options(confirm_with_uv=...)` (#382); concentration-free
  volume-of-correlation mass `Component.get_volume_mass`, `SecSaxsData.get_volume_mass_curve`, default q cut 0.3 (#381);
  `Component.get_xy`, `xr_peakpositions` as a list, documented `plot_compact` axes (#383); mapping-quality and implausible-Rg
  warnings (#371, #372); `Species(shape=...)` and `continuum_species` (#373); folded/unfolded form factors and
  `simulate_ssd` instrument options (#379); Kratky curves without the shape library, `molass.set_progress`, Rg-curve disk cache,
  `version_info` (#374-#378).
- **Requires:** `molass_legacy>=1.7.2`.

## 1.2.3 (2026-11-07)
- **Added:** `Decomposition.get_continuity_report()` and `ContinuityReport.plot()` (#370).
- **Fixed:** EDM `b = 0` for components that may not front in the quick stage (`tailing_b` option, #349); the sub-frame peak core
  is guarded against a larger neighbouring peak (#368); analysis summary and freeze, Rg-curve cache, shape-match API,
  `RgCurve.reliable`, notice of changed defaults (#354, #359-#363).

## 1.2.2 (2026-10-30)
- **Changed:** Trimming keeps the low-q points by default (`small_angle_limit`, #342). Fronting only where the quick EGH fit
  shows it: `fronting=` option, recipe key `fronting`, EGH tau and EDM b bounds (#350). `load_analysis_session` loads the best job,
  not the latest (#343). No module reload by default (#347). Interparticle detection threshold 0.95 (#342).
- **Added:** `molass.load_analysis` (#344), `molass.analysis_status` and `diagnose()` (#352, #353), `Component.skewness`
  (#355), `optimize_rigorously(note=...)` (#357), `molass.Homogeneity` (#323-#330), `NoCompletedJobError` (#336),
  `RunInfo.is_done` / `wait_until_done`, `load_best_rigorous_result`, did-you-mean `AttributeError`, `molass.Testing.simulate_ssd`
  (#333-#340), Mapping vocabulary (`Mapping.slope`, `xr_to_uv`, ...) (#331), `RgCurve.i0s` (#322),
  `molass.SEC.Models.EdmFunction.edm_curve` (#356).
- **Requires:** `molass_legacy>=1.7.2`.
