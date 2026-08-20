# DESIGN: Reverse `optimize_rigorously()`'s `in_process` default to `False`

**Status**: Decision made (2026-08-20) — implementation pending
**Context**: Follow-up to `DESIGN_split_optimizer_architecture.md` (April 22, 2026) and
`DESIGN_inprocess_monitor.md` (April 27, 2026). Triggered by a molass-gui "Continue in
Notebook…" feature discussion that surfaced a real performance/architecture question about
which mode should be the *default* for `Decomposition.optimize_rigorously()`.

---

## How this came up

While simplifying molass-gui's generated "Continue in Notebook…" export (dropping
GUI-specific parameters in favor of library defaults, per a general "options for power
users, defaults for general users" principle adopted this session), the notebook stopped
passing `in_process=False` and started relying on the library default (`True`). This raised
the question: should the exported notebook instead match the GUI's own default
(`in_process=False`, subprocess via `pipeline_recipe`), and if so, should that be achieved
by changing the *library's* default instead of the GUI's or the notebook's?

## Evidence gathered

1. **Original rationale for `in_process=True` as the library/notebook default**
   (`DESIGN_split_optimizer_architecture.md`, April 22, 2026): subprocess was designed for
   the *tkinter* constraint (`mainloop()` must not block). It was inherited uniformly by the
   library/notebook path "because it was already there," even though notebooks have no such
   constraint (kernel I/O runs on a separate iopub thread). This caused a real bug class
   (#117/#118/#119 — subprocess and parent built divergent optimizers, producing different
   `fv` for the same params). The split architecture fixed this by making the notebook path
   in-process by construction (no re-derivation, no divergence possible).

2. **molass-gui's own history** (recovered from a past chat session via `session_store_sql`,
   session `8500c8a8-6f7f-4e40-9eeb-516b93dab422`, turn 6): the GUI's "Use subprocess"
   checkbox defaults to checked *not* for crash isolation, but for **measured performance**:
   the GUI's live dashboard re-evaluates the full `objective_func(params, plot=True)` every
   3 seconds to redraw, estimated at **~13-28% total overhead** on a 30-minute run (watch-loop
   evaluations ~10-20%, `_objective_lock` contention ~2-5%, Tkinter event loop ~1-3%),
   translating to roughly **13-15% faster wall-clock time** for subprocess mode on long runs.

3. **This overhead is a library-level property, not GUI-specific.** Re-reading
   `MplMonitor.update_plot()` (`molass-legacy/molass_legacy/Optimizer/MplMonitor.py`), the
   in-process "external watcher" dashboard (`DESIGN_inprocess_monitor.md`'s Phase 5) reads
   `callback.txt` cheaply for the best params, but then **still calls the full
   `objective_func()`** on the live, actively-running optimizer to render the UV/XR/Score
   panels (`display_optimizer = self.monitor_optimizer or self.optimizer`). The code's own
   comment confirms this: *"Issue #50: prevent concurrent objective_func access when using
   the live in-process optimizer... The lock is held through both `plot_job_state()` and
   `_build_monitor_snapshot_json()` since both call `objective_func()`."* So any caller using
   `in_process=True, monitor=True` — GUI or notebook — pays this same lock-contention /
   redraw cost during long monitored runs.

4. **The state-divergence risk that motivated in-process (#117/#118/#119) has a separate,
   already-validated fix for subprocess mode**: `pipeline_recipe` (Option E, "recipe-based
   subprocess," implemented and validated 2026-08-05/06 — see the superseded top section of
   `/memories/repo/molass-gui-prototype-status.md`). Instead of the subprocess re-deriving
   state ad-hoc from disk (the actual cause of #117-#119), it reconstructs deterministically
   from an explicit, declarative recipe dict. This decouples "subprocess" from "divergence
   risk" — the divergence bug was a symptom of *how* the old subprocess path re-derived
   state, not an inherent property of running out-of-process.

5. **The key reframing that changed the conclusion**: molass's `quick_decomposition()` vs
   `optimize_rigorously()` split already separates "fast, low-precision" from "slow,
   high-precision" use. A user who reaches for *rigorous* optimization at all has already
   selected into needing precision or tackling a hard case — for SEC-SAXS research this
   routinely means hours, sometimes longer (dedicated experiment time, not a quick check).
   So "the general user of `optimize_rigorously()`" is not the same population as "the
   general user of molass" — for this specific function, a long run is the *typical* case,
   not a rare power-user tail case. That means the ~13-28% overhead, and the crash-isolation
   benefit, both matter for the *mainline* use of this function, not an edge case to be
   opted into.

## Decision

Change `Decomposition.optimize_rigorously()`'s default from `in_process=True` to
`in_process=False`, with `pipeline_recipe` auto-constructed by default (mirroring
molass-gui's own current behavior) rather than treated as a deprecated fallback path.

This **reverses** the specific default-value choice made in
`DESIGN_split_optimizer_architecture.md` Phase 2/4 (`in_process=True` as the opt-in-turned-
default), while keeping that document's underlying architectural fix (deterministic,
recipe-based subprocess reconstruction, avoiding #117-#119-style divergence) as the
mechanism that makes subprocess-by-default safe to reinstate.

## Required implementation changes (not yet done)

1. `Decomposition.optimize_rigorously()` (`molass/LowRank/Decomposition.py`): change
   `in_process=True` → `in_process=False` in the signature.
2. `make_rigorous_decomposition_impl()` (`molass/Rigorous/RigorousImplement.py`): same
   default flip; the function's `**kwargs`/default handling needs to auto-construct
   `pipeline_recipe` (from current decomposition/trim/baseline/model state) when the caller
   doesn't supply one, matching what `upgraded_view.py` already builds explicitly today —
   this makes the auto-construct path the *normal* default flow, not a deprecated fallback.
3. The existing `DeprecationWarning` text ("Prefer `in_process=True` (the default)...") is
   now backwards and must be rewritten or removed — it was written when `in_process=False`
   was the legacy/deprecated path; after this change it becomes the default, sanctioned path.
4. Audit ripple effects before landing:
   - Tests that assert `in_process=True` as default behavior (e.g.
     `tests/specific/200_Rigorous/test_090_pattern_a_warning.py`,
     `test_100_cma_async_fallback.py`) will need updating.
   - Tutorials/docs (`tests/tutorial/11-rigorous_optimization.py`) and any
     molass-researcher notebooks relying on the current default's in-process behavior
     (variables staying alive across cells, no subprocess startup cost) need review.
   - The CMA async-crash auto-fallback logic (`in_process=True, async_=True` → falls back
     to `in_process=False`) becomes a no-op once `in_process=False` is already the default —
     should be simplified/removed rather than left as dead code.
5. molass-gui side: once the library default matches the GUI's own behavior, the GUI's "Use
   subprocess" checkbox and the notebook export's explicit `in_process=`/`pipeline_recipe=`
   parameters can both be simplified/dropped, since both now get the right behavior "for
   free" from the library default — achieving the original goal (GUI and notebook
   equivalent, notebook stays simple) without either side needing to fight the library's
   own default.

## Status

Decision recorded; no code changes made yet. Next session should implement steps 1-4 above,
starting with a fresh regression baseline (best fv, best SV, wall time) per the original
split-architecture document's own methodology, before touching the default.
