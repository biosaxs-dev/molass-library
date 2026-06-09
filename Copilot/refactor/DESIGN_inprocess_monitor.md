# DESIGN: In-Process MplMonitor Equivalent

**Status**: Discussion / proposal — resumes deferred Phase 5 of `DESIGN_split_optimizer_architecture.md`
**Date**: April 27, 2026
**Context**: Follow-up to `DESIGN_split_optimizer_architecture.md` and issue molass-library#137 (`async_=True` + `RunInfo.is_alive`)

---

## Why we left MplMonitor in the first place

This work is not new — it's the resumption of a piece deliberately deferred when
the split architecture landed. To avoid relitigating that decision, the chain of
events:

1. **Original sin (tkinter era)** — `MplMonitor` was built around a subprocess
   writer because the legacy GUI's `mainloop()` would freeze if the optimizer
   ran in-process. Subprocess + `callback.txt` was the right answer *for tkinter*.
2. **Mistake propagated** — when the library/notebook path was added, it
   inherited the subprocess architecture by default, even though the notebook
   kernel has no event loop in user code's path. We paid the cost (state
   divergence, re-derivation, lost variables) without the benefit.
3. **Bugs surfaced (#117 / #118 / #119)** — parent and subprocess each built
   their own optimizer; they returned different `fv` for the same params.
   `MplMonitor` showed parent-side `fv`, `callback.txt` logged subprocess-side
   `fv`. The widget literally lied.
4. **Tactical patch (Fix 1, #118)** — give `MplMonitor` a `monitor_optimizer`
   built via `create_optimizer_from_job` so its display matches the subprocess.
   Worked, but didn't fix the underlying mismatch (subprocess still couldn't see
   the parent's prepared data).
5. **Structural fix attempt (Fix 2, #119)** — pickle parent assets to the
   subprocess. Regressed badly (`fv = 254,372`, SV = −100). Lesson: subprocess
   optimizer state is the result of a *derivation pipeline*, not a bag of
   arrays.
6. **Decision (April 22, 2026)** — split architecture: notebook path runs
   in-process; the parent-built optimizer *is* the one that runs. Divergence
   becomes structurally impossible.
7. **`MplMonitor`'s fate** — hard-wired to `BackRunner` in `__init__`. The
   in-process path therefore had to skip it. Phase 2 of the split-architecture
   design replaced it with `tqdm`/live-matplotlib alternatives; Phase 5
   (`progress="dashboard"` — reuse `MplMonitor`'s widget with an in-process
   callback) was explicitly listed but **deferred**.

So we didn't leave `MplMonitor` because of `MplMonitor` — we left it because
the subprocess writer it was wired to couldn't be fixed for the notebook path.
What this document proposes is precisely the deferred Phase 5: bring the
dashboard back, now that the writer lives in the same process.

---

## Problem

Since v0.9.4, `optimize_rigorously()` defaults to `in_process=True`. With `async_=True` (issue #137) the optimizer runs in a daemon thread and `RunInfo` is returned immediately, so the kernel main thread stays idle and interactive.

What's missing: a **live visual monitor** equivalent to the existing `MplMonitor` (which is bound to the subprocess path via `BackRunner`). Current monitoring story for in-process is:

- `aicKernelEval("run_info.live_status()")` — scalar snapshot, AI/external only
- Re-run a probe cell manually — discrete, not live
- `run_info.plot_sv_history()` — only after the run

User wants: an MplMonitor-equivalent dashboard that renders **while the optimizer is running in-process**.

---

## What MplMonitor actually is

Three layers (in `molass_legacy/Optimizer/MplMonitor.py`):

1. **ipywidgets dashboard** (`Output` + status labels + Resume/Terminate/Export buttons) — built on the main thread
2. **Watcher thread** (`watch_progress`, ~1 s interval) — polls `JobState`, calls `update_plot()` when changed
3. **`JobState`** — reads `callback.txt` from disk; agnostic to who writes it

**Key insight**: `JobState` only cares that `callback.txt` exists and gets updated. The subprocess specificity is concentrated in:
- `runner.poll()` → "is the writer still alive?"
- `runner.terminate()` → kill the writer
- BackRunner construction in `MplMonitor.__init__`

For in-process, the equivalents are:
- `run_info.is_alive` → "is the writer still alive?"
- (terminate not yet implemented — see Open questions)

---

## Why this is feasible right now

When `async_=True`:
- The optimizer thread writes `callback.txt` exactly like the subprocess does
- The kernel main thread is idle → ipywidgets messages flow normally
- The `_t.join(timeout=0.05)` GIL-release loop in `InProcessRunner` (molass-legacy#26) gives the watcher thread enough GIL slices to update the figure

So the existing `JobState` + `update_plot` machinery should work unmodified, with only the source-of-truth swap (BackRunner → RunInfo).

---

## Coupling audit — what's actually subprocess-specific in MplMonitor

Reading `molass_legacy/Optimizer/MplMonitor.py` end-to-end, the BackRunner
coupling is concentrated in a small, enumerable surface:

| Where | What | In-process equivalent |
|---|---|---|
| `__init__` | `self.runner = BackRunner(...)` | `self.runner = run_info` (or `None`) |
| `watch_progress` | `ret = self.runner.poll()` | `not run_info.is_alive` |
| `watch_progress` | `self.runner.terminate()` | cooperative flag (or hide button) |
| `run_impl` | starts the subprocess via `runner.run(...)` | already done by `optimize_rigorously(async_=True)` |
| `working_folder` | `self.runner.working_folder` | `run_info.work_folder` |

Everything else — `JobState`, `update_plot`, the ipywidgets dashboard,
`save_the_result_figure`, `_write_run_complete_json`, the per-axis JSON
sidecar (#22), `monitor_optimizer` indirection (#118), anomaly bands, log-handler
setup, the active-monitor registry — is **source-agnostic**. It already reads
from `callback.txt`, which the in-process path also writes.

**Implication**: spinning up a parallel `InProcessMonitor` class would duplicate
~700 lines of polish that took multiple bug fixes (#22, #118, #AI-B, #128) to
get right. Every future fix would need to be applied twice. That's a maintenance
trap.

---

## Options

| Option | What | Effort | Caveats |
|--------|------|--------|---------|
| **A. `RunInfo.show_monitor()`** new method | New thin class `InProcessMonitor` that composes `JobState` + a copy of `update_plot` + dashboard, replacing `runner.poll()` with `run_info.is_alive` | Medium (~1 day) | Code duplication with MplMonitor unless refactored |
| **B. Refactor MplMonitor with `ProgressSource` interface** | Pluggable: `SubprocessSource` (BackRunner) or `InProcessSource` (RunInfo). MplMonitor accepts either | Larger (~2–3 days) | Risk of breaking subprocess path; needs thorough tests |
| **C. `optimize_rigorously(monitor='inline', async_=True)`** | Library auto-spawns the in-process monitor; no extra call needed. Sugar on top of A or B | Small (after A/B) | API decision |
| **D. AI-only polling helper** `run_info.poll_until_done(callback=fn)` | No widget; calls `fn(live_status())` from the main thread | Small (~1 hour) | Not visual; same blocking issue we just hit in 13u cell [7] |

---

## Recommendation

This is the deferred Phase 5 (`progress="dashboard"`) of the split-architecture
design. The coupling audit above shows the BackRunner surface inside MplMonitor
is small and concentrated, so:

1. **Option B is the recommended path** — refactor MplMonitor to accept a
   pluggable source object. The minimal refactor is:
   - **Source protocol**: an object with `is_alive() -> bool`, `terminate() -> None`
     (optional / no-op), and `working_folder -> str`.
   - **Two factories** instead of branching:
     - `MplMonitor.for_subprocess(...)` — builds `BackRunner`; renamed current behavior, no logic change.
     - `MplMonitor.for_run_info(run_info)` — uses `RunInfo`, no `BackRunner`.
   - **Three call sites change**: `runner.poll()` → `source.is_alive()`,
     `runner.terminate()` → `source.terminate()`, `runner.working_folder` →
     `source.working_folder`.
   - **Dashboard variant**: hide Resume + Terminate buttons when source is
     in-process (no clean kill, niter is what it is).
   - **Risk control**: land behind a feature flag; run both paths through the
     existing tutorial tests before flipping any default.

2. **Option A is rejected** — a parallel `InProcessMonitor` class duplicates
   ~700 lines and creates a long-term double-maintenance burden.

3. **Option C** (`progress="dashboard"` argument to `optimize_rigorously`) is
   the API surface on top of B — the surface the original Phase 5 promised.

### Refactor sketch (subprocess path stays byte-identical)

```python
# molass_legacy/Optimizer/MplMonitor.py (additions)

class _SubprocessSource:
    def __init__(self, runner): self._runner = runner
    def is_alive(self):         return self._runner.poll() is None
    def terminate(self):        self._runner.terminate()
    @property
    def working_folder(self):   return self._runner.working_folder

class _RunInfoSource:
    def __init__(self, run_info): self._ri = run_info
    def is_alive(self):           return self._ri.is_alive
    def terminate(self):          pass   # cooperative — see Open Q #1
    @property
    def working_folder(self):     return self._ri.work_folder

class MplMonitor:
    def __init__(self, source, function_code=None, clear_jobs=True, ...):
        self.source = source
        # ... rest of existing __init__, but s/self.runner.…/self.source.…/

    @classmethod
    def for_subprocess(cls, *, xr_only=False, **kw):
        from .BackRunner import BackRunner
        return cls(_SubprocessSource(BackRunner(xr_only=xr_only, shared_memory=False)), **kw)

    @classmethod
    def for_run_info(cls, run_info, **kw):
        return cls(_RunInfoSource(run_info), **kw)
```

All three call-site changes are mechanical search-and-replace within
`watch_progress` and `working_folder`. No widget code, no `JobState` code,
no `update_plot` code is touched.

### API surface (Option C, on top of B)

```python
run_info = decomp.optimize_rigorously(
    rgcurve, method='BH', niter=20,
    in_process=True, async_=True,
    progress='dashboard',     # 'tqdm' | 'plot' | 'dashboard' | None
)
# 'dashboard' → internally calls
#   MplMonitor.for_run_info(run_info).create_dashboard().show().start_watching()
```

---

## Open questions

1. **Terminate semantics**: subprocess MplMonitor can `runner.terminate()` (SIGTERM). In-process has no clean equivalent — can't kill a thread. Options: cooperative flag the optimizer checks, or simply omit the Terminate button for in-process.
2. **Dashboard reuse**: how much of MplMonitor's widget tree (status labels, buttons, save-figure path) belongs in the in-process variant? Probably a stripped-down version (no Resume — niter is what it is; no Terminate — see #1).
3. **Multiple panels**: MplMonitor draws optimizer-state plots beyond just SV history (panel 3 = best-params snapshot). For in-process we need access to the live `optimizer` object, which `RunInfo` already has (`run_info._optimizer` or similar — to be checked).
4. **Naming**: `show_monitor()` vs. `display_monitor()` vs. `monitor()`. Symmetry with `live_status()` suggests `live_monitor()`.

---

## Related

- `DESIGN_split_optimizer_architecture.md` — parent doc; this is its deferred Phase 5
- Issue molass-library#117 / #118 / #119 — the parent/subprocess `fv` divergence that motivated the split
- Issue molass-library#137 — `async_=True` + `RunInfo.is_alive` (merged); prerequisite for live monitoring
- Issue molass-library#138 — NS (UltraNest) segfaults in-process
- molass-legacy#26 — GIL-release loop in `InProcessRunner` (prerequisite — without it the watcher thread can't get GIL slices to redraw)
