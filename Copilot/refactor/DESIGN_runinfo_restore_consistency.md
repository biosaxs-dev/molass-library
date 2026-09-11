# RunInfo `restore()` — design reconsideration

**Status**: 🔬 Open design question, not yet implemented.

Raised because `restore()`/`load_best()` trusts whatever `decomp` the caller
passes in, with **no validation** against what was actually optimized in
`analysis_folder`. Source: chat discussion +
`molass-papers/experiments/recipe_runner_notebook_redesign.ipynb` (Sections 4, 9, 10).

## Table 1 — Patterns to construct a `RunInfo` (other than `Decomposition.optimize_rigorously()`)

| # | Entry point | What it needs | What you get |
|---|---|---|---|
| 1 | `RunInfo.reconnect(analysis_folder)` (classmethod) | Just a folder path — reads `RUN_MANIFEST.json` + job dirs from disk | `RunInfo` with **no live optimizer/ssd** (`optimizer=None`, `ssd=None`). Supports `live_status()`, `sv_history`, `load_best()`, `plot_sv_history()`. `get_score_breakdown()`/`diagnose()` won't work (no optimizer). For reconnecting after a kernel restart. |
| 2 | `molass.Rigorous.RunInfo.restore(decomposition, analysis_folder, rgcurve=None)` | A `decomposition` you already have in-session + the folder | Thin wrapper over #1 (calls `reconnect()` internally), then attaches your `decomposition`/`ssd`/`rgcurve` so it *looks* like a live run. Documented replacement for deprecated `Decomposition.load_best_rigorous_result()`. |
| 3 | `molass.Rigorous.GuiReplay.load_gui_scenario(analysis_folder)` → `.run_inprocess(method=..., niter=...)` | A folder produced by the **legacy tkinter GUI** (`callback.txt`, `init_params.txt`, `ip_*.npy`, ...) | Reconstructs the GUI's optimizer in-process, launches a *brand-new* run from that state, returns a fresh `RunInfo`. Purpose: compare a notebook BH/DE run against a completed legacy-GUI run on the exact same data. |
| — | Raw `RunInfo(ssd=..., optimizer=..., dsets=..., init_params=..., ...)` constructor | technically public | In the codebase, only ever called directly in unit tests (bare/fake object) and inside `GuiReplay.run_inprocess()` (pattern 3's internals). Not an independent user-facing pattern. |

Not separate patterns (commonly mistaken for such):
- `RigorousImplement.py` builds `RunInfo(...)` directly in 2 places (in-process vs
  subprocess branch) — both internal to `make_rigorous_decomposition_impl()`,
  reached only via the single public `optimize_rigorously()` call.
- `compare_optimization_paths()` just calls `optimize_rigorously()` once per path
  and bundles the two `RunInfo`s into a `ComparisonResult` — built on top, not new.

## Table 2 — Conditions that must all hold for `restore()`/`load_best()` to be correct (beyond model name + component count)

`load_best()` → `CurrentStateUtils.load_rigorous_result()` rebuilds a "for-split-only"
optimizer from **whatever `decomp` you pass**, then calls
`optimizer.split_params_simple(saved_params)`. It does **not** read
`analysis_folder/optimized/recipe.json` (the ground truth) at all — full
correctness depends entirely on the caller's `decomp` matching by construction.

| Requirement | Why | Evidence |
|---|---|---|
| Same `pore_dist`/`rt_dist` for SDM | `detect_function_code()` maps `('mono','gamma')→G1200`, `('lognormal','gamma')→G1300`, etc. G1200/G1300 have **different parameter counts** (G1300 adds shared `mu`, `sigma_pore`). "model=sdm" alone is not enough. | `molass/Rigorous/FunctionCodeUtils.py` `FUNCTION_CODE_MAP` |
| Same `num_components` | Per-component parameter blocks scale directly with this. | `construct_legacy_optimizer(num_components=decomp.num_components, ...)` in `CurrentStateUtils.load_rigorous_result` |
| Same underlying `ssd`/trim/correction | Component curves are reconstructed directly on `decomp.ssd`'s frame axis (`ssd.xr.get_icurve()`). A `decomp` built from a differently-trimmed/corrected SSD places the right numbers on the wrong axis/baseline shape. | Same function, `ssd = decomp.ssd` |
| Same baseline type / UV presence | Baseline parameter count differs (2 vs 3 for XR linear/integral; UV block only if `ssd.has_uv()`) — part of the saved `params`'s layout. | Same function, `separated_params` split |

**Failure mode**: not always a clean crash. Pure length mismatch (e.g. wrong
`num_components`) tends to raise a cryptic `ValueError`/`IndexError` deep in
`split_params_simple` (same error class hit twice already in
`recipe_runner_notebook_redesign.ipynb` while fixing unrelated bugs). If lengths
coincidentally match while semantics differ (e.g. mono vs lognormal SDM with same
total param count), it silently misassigns numbers — no error, wrong result.

## Why this is safe today in practice

`recipe_runner_notebook_redesign.ipynb` Section 7 Option B and Section 10's
caching prototype are both safe because `decomp` always comes from
`RecipeRunner.rebuild_decomposition_from_recipe(analysis_folder)`, which reads
`recipe.json` itself and rebuilds `decomp` faithfully — consistency guaranteed by
construction, not luck. The risk only appears if someone hand-builds/reuses a
`decomp` NOT derived from that specific recipe and passes it to `restore()`
directly — nothing currently catches that mismatch.

## Candidate fix (not yet decided/implemented)

`restore()`/`load_rigorous_result()` could cross-check the passed `decomp`
against `analysis_folder/optimized/recipe.json`'s stored `function_code`/
`num_components` (and raise/warn on mismatch) before trusting it — closing the
gap without forcing every caller through `rebuild_decomposition_from_recipe`.
Follow the same AI Improvement Feedback Loop (issue → implement → test → close,
`molass-library/Copilot/copilot-guidelines.md` Rule 11) if this gets picked up.
