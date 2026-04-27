# Design: Split Architecture for Rigorous Optimization

**Status**: Approved (April 22, 2026) — implementation pending  
**Tracking**: Umbrella issue TBD; supersedes the unfinished work in #117 / #119

---

## Problem

Today, `optimize_rigorously()` always spawns an optimizer subprocess via `BackRunner` →
`subprocess.Popen`. The subprocess re-derives its data (`dsets`, `qvector`,
`xr_base_curve`, peak/Guinier setup) from `in_folder` via `OptimizerInput`, while the
parent process holds an independently constructed optimizer with its own derivation.

Two problems follow:

1. **Display divergence (#117 / #118)** — `MplMonitor` shows parent-side `fv`,
   `callback.txt` logs subprocess-side `fv`. Resolved tactically by Fix 1 (#118):
   the monitor now uses a `monitor_optimizer` built via `create_optimizer_from_job`
   so its display matches the subprocess.
2. **Architectural divergence (#119)** — even after Fix 1, the subprocess still
   doesn't see the library-prepared data (anomaly masks, custom `uv_monitor`,
   `nsigmas`, etc.). The first attempt to fix this by pickling parent assets to
   `prepared_optimizer.pkl` regressed badly: subprocess `GuinierDeviation` set
   nonsense regions (q ≈ 0.18) → `fv = 254,372` → `SV = -100`. The lesson: the
   subprocess's optimizer state is the result of a derivation *pipeline*, not a
   bag of arrays. Hand-transferring outputs creates an unbounded compatibility
   surface.

## Why notebook UI and tkinter UI need different architectures

The reason a single architecture doesn't fit both comes down to **who owns the
event loop** and **what blocking the main thread does to the user**.

### Tkinter GUI

Tkinter has its own event loop (`mainloop()`) running in the main thread. That
loop processes window events, redraws widgets, and keeps the window responsive
to the OS. If a long computation runs in the same thread, the loop stops
pumping events: the window freezes, redraws stop, the OS may mark it
"Not Responding".

Threading doesn't help much in CPython:
- The GIL serializes Python bytecode execution.
- Tkinter itself is **not thread-safe** — widget updates from a non-main thread
  are undefined behavior.
- A worker thread doing heavy numpy/scipy work *would* release the GIL during
  C calls, so the GUI thread could keep pumping events. But the worker can't
  safely touch widgets directly; all UI updates must be marshalled back via
  `after()` or queues. This works but is fragile.

→ **Subprocess is genuinely the cleanest answer for tkinter.** The optimizer
runs in a separate OS process; the GUI thread is never blocked. The GUI polls
files (`callback.txt`) or pipes from its event loop — `mainloop()` keeps
spinning, redraws happen, the window stays responsive. If the optimizer
crashes, the subprocess dies and the GUI logs it; the application survives.

### Jupyter notebook

Notebooks have **no GUI event loop in your code's path**. The kernel is a
request-response server: you execute a cell, the kernel runs that code
synchronously, output streams back to the browser, the cell finishes.

While a cell is running, there is no UI in your code that needs servicing.
The notebook UI itself (cell execution indicator, "Interrupt" button) is
served by the **kernel front-end** in the browser, talking to the kernel via
ZeroMQ. That communication is handled by the **iopub thread** inside ipykernel
— completely separate from your Python code's thread.

What this means concretely:
- A long-running cell **does not** freeze the notebook UI. The "stop" button
  keeps working. Other cells can be queued. Progress prints stream out as
  they happen.
- You don't need a separate process to keep the UI responsive. The kernel
  architecture *already* gives you that separation, for free, between your
  code and the UI.
- Variables stay alive across cells in the same kernel — that's the whole
  point of the notebook workflow. A subprocess throws that away by
  re-deriving everything from disk on each run.

### The core asymmetry

| | Tkinter GUI | Notebook |
|---|---|---|
| Where the UI lives | **Same process** as your code | **Browser**, talking to kernel via ZMQ |
| What "blocking" means | Window freezes, OS marks unresponsive | Cell hasn't finished yet — UI fine |
| What needs the main thread | The event loop, at all times | Nothing — kernel handles its own protocol |
| Cost of running computation in-process | UI dies | Just normal cell execution |
| Cost of running in subprocess | Necessary for responsiveness | Loses parent state, requires re-derivation, creates the divergence we hit |

The subprocess architecture was *designed for the tkinter constraint* ("the
optimizer must not block `mainloop()`"). It then got applied uniformly to the
library path because it was already there. But the library/notebook path
doesn't have that constraint — there's no `mainloop()` to protect. We pay
the cost (state divergence, file-based IPC, lost variables on each run)
without getting the benefit.

Splitting the architecture is just letting each path use what its UI model
actually requires.

## Decision

Adopt a **split architecture**:

- **GUI path** (legacy tkinter app): unchanged. `BackRunner` → subprocess →
  `OptimizerInput` re-derivation. Process isolation keeps the GUI responsive
  and survives optimizer crashes.
- **Library / notebook path**: the optimizer runs **in the same process** as
  the parent. The optimizer object the library already built (with library-prepared
  data) is the one that runs. No subprocess, no re-derivation, no divergence.

### Rationale

- Eliminates the bug class for the workflow where it actually hurts.
- The subprocess approach is correct *for tkinter* (GIL would freeze the GUI in a
  thread; threads are still inappropriate for that use case under CPython 3.13/3.14
  GIL). It is wrong *for notebooks*, where the parent is already prepared and the
  data is already in memory.
- Avoids the speculative "fully hoist all subprocess derivation parent-side"
  refactor (Option 2) until we have evidence it's needed.
- Trade-off accepted: the notebook kernel can be killed by a hard optimizer
  crash (segfault, `os._exit`, OOM, uninterruptible C loop). Mitigated by Phase 1
  step 3 (audit `exit()` calls) and optional Phase 5 (`isolated=True` flag).

## Plan

### Phase 0 — Prep

- Open umbrella issue (this document is the design body).
- Comment on #119 pointing to the umbrella; keep #117 / #119 open until Phase 4.
- Capture baseline numbers (best fv, best SV, wall time) on Apo 1c with the
  current subprocess path. This is the regression target.

### Phase 1 — Extract in-process entry point in `molass-legacy`

- New: `molass_legacy/Optimizer/InProcessRunner.py` exposing
  `run_optimizer_in_process(optimizer, init_params, bounds, niter, seed, solver,
  callback, work_folder=None) -> result`.
- Reuse the optimizer object the library already built. **Do not** call
  `create_optimizer_from_job` from this path.
- Logic mirrors `OptimizerMain.optimizer_main`'s post-construction work:
  `prepare_for_optimization`, solver dispatch (BH / NS / UltraNest / MCMC / SMC),
  callback wiring, `callback.txt` writes (kept for tooling compatibility).
- Audit `exit(-1)` / `sys.exit()` paths in `OptimizerMain`, `BasicOptimizer`,
  solver wrappers — replace with raised exceptions. File one issue per finding
  (`AI-friendliness: replace exit(-1) in <module>`); fix incrementally.
- Route `optimizer.log` writes through Python `logging` so notebook users see
  warnings/errors in-cell.

### Phase 2 — Add `in_process=True` opt-in to `optimize_rigorously()`

- Parameter added to `molass/Rigorous/RigorousImplement.py::optimize_rigorously`,
  default `False` for the opt-in phase.
- When `True`: skip `BackRunner.run`; call `run_optimizer_in_process` on the
  parent's `optimizer`. Reuse the existing job-folder layout
  (`init_params.txt`, `bounds.txt`, `callback.txt`, `optimizer.log`) so
  `load_rigorous_result`, `list_rigorous_jobs`, `plot_convergence` keep working.
- `RunInfo.wait()` becomes a no-op for in-process runs (synchronous from Python's
  POV). Start synchronous; revisit threading later if UX demands it.
- Skip `MplMonitor` for in-process runs. Provide a simple progress callback
  (tqdm or live matplotlib) driven directly from the optimizer's per-iteration
  callback. Cleaner than today — no file polling.

#### Phase 2 step 3 — Default progress UX

The in-process path replaces `MplMonitor`'s file-polling bridge with a direct
Python callback. Three layered patterns, opt-in by argument:

**Pattern 1 — `tqdm` (default, `progress="tqdm"`)**

Single live line in the cell output, equivalent to today's `MplMonitor` title.

```python
from tqdm.auto import tqdm
pbar = tqdm(total=niter)
best = [float("inf")]

def cb(params, fv, accepted):
    best[0] = min(best[0], fv)
    pbar.set_postfix(best_sv=f"{convert_score(best[0]):.2f}",
                     cur_sv=f"{convert_score(fv):.2f}",
                     acc=accepted)
    pbar.update(1)
```

**Pattern 2 — Live matplotlib (`progress="plot"`)**

SV trajectory + (throttled) 3-panel decomposition snapshot, equivalent to
today's `MplMonitor` dashboard.

```python
%matplotlib widget
fig, axes = plt.subplots(ncols=4, figsize=(20, 4))
ax_sv = axes[-1]; fvs = []

def cb(params, fv, accepted):
    fvs.append(fv)
    ax_sv.clear()
    ax_sv.plot([convert_score(f) for f in fvs])
    if len(fvs) % 5 == 0:                     # throttle
        for ax in axes[:3]: ax.clear()
        optimizer.objective_func(params, plot=True,
                                 axis_info=(fig, list(axes[:3]) + [None]))
    fig.canvas.draw_idle()
```

The `optimizer` here is the parent's prepared object — by construction the
plotted state is the optimized state, so #117 / #118 / #129-class divergence
is unreachable.

**Pattern 3 — Reuse `MplMonitor` widget (`progress="dashboard"`, Phase 5)**

`MplMonitor`'s rendering (ipywidgets dashboard, Resume/Terminate/Export
buttons, anomaly bands) is independent of *how* params arrive. The
in-process callback can call `monitor.update(params, fv)` directly — same
widget, no file polling, no `monitor_optimizer` indirection.

**User control mapping (vs today):**

| Today (subprocess + MplMonitor) | In-process |
|---|---|
| Resume / Terminate buttons | Kernel "Interrupt" (`KeyboardInterrupt` in callback or solver) |
| File-polled best SV in title | `min(fvs)` in callback |
| 3-panel decomposition snapshot | `objective_func(params, plot=True, axis_info=...)` from callback |
| Export job folder | Same — Phase 2 keeps `callback.txt` / `init_params.txt` writes |
| Crash isolation | Lost on default path; recovered via `isolated=True` (Phase 5) |

**API shape:**

```python
optimize_rigorously(decomposition, rgcurve,
                    in_process=True,
                    progress="tqdm",        # "tqdm" | "plot" | "dashboard" | None
                    progress_every=1,        # throttle for "plot" / "dashboard"
                    callback=None)           # user callback, runs after built-in UX
```

`callback=None` is the escape hatch — power users skip the built-in UX and
get the raw `(params, fv, accepted)` stream.

### Phase 3 — Validation

- In `molass-researcher/experiments/13_rigorous_optimization/13g_rigorous_apo_1c.ipynb`,
  add a cell that runs the same problem twice (`in_process=False` vs `True`)
  and compares `best_fv`, `best_sv`, Rg outputs, runtime.
- Add `molass-library/tests/specific/200_Rigorous/test_in_process_parity.py`:
  on a deterministic small case (fixed seed, `niter=2`),
  `assert abs(fv_subprocess - fv_in_process) < tol`.
- Run on Apo 1c, Apo 2c, and the SDM-lognormal cases from #108 / #111. Document
  any divergences in the umbrella issue. Each surviving divergence becomes its
  own issue (it cannot be a sync problem at this point — same process, same
  optimizer object).

### Phase 4 — Flip default & retire workarounds ✅ (April 27, 2026, commit 563e080, v0.9.4)

- ✅ Changed default to `in_process=True` in `RigorousImplement.py`.
- ✅ Closed #117 and #119 — divergence no longer reachable on the default path.
- ✅ Fix 1 (#118 `monitor_optimizer`) kept in place — still useful for subprocess monitoring path.
- ✅ Convention 9 in `.github/copilot-instructions.md` updated with split-architecture table.
- ✅ Version bumped to 0.9.4; `PROJECT_STATUS.md` updated.

### Phase 5 — Optional hardening

- `isolated=True` flag wrapping the in-process call in
  `concurrent.futures.ProcessPoolExecutor` for crash safety. Same code path,
  forked child inherits parent's prepared optimizer object — no data-divergence
  risk.
- Parallel jobs (`niter > 1` with multi-start) via `ProcessPoolExecutor` — replaces
  today's per-job subprocess fan-out.
- Optional `timeout_per_job` watchdog to cancel hung runs.

## What we'd do first

Phases 0, 1 (steps 1–2), 2 (steps 1–2), 3 (step 1). That's the smallest slice that
gets the in-process path running end-to-end and produces the side-by-side comparison
needed to justify Phase 4.

## Non-goals

- Removing the subprocess code or the legacy GUI's dependency on it.
- Unifying GUI and library on a single architecture (Option 2) — explicitly
  rejected as too much speculative work given today's evidence.
- Shared memory as a primary fix — addresses transport cost, not the semantic
  mismatch we hit. May appear later as an internal detail of `isolated=True`.

## Open questions

- Should `in_process=True` runs still write `callback.txt`, or emit results via
  a richer Python object only? Decision: yes, keep file output for reproducibility
  and tooling compatibility. Re-evaluate after Phase 3.
- How should the in-process path surface progress? Simple `tqdm` first; a
  matplotlib live plot is a Phase 5 nice-to-have.

## Phase 0 baseline (subprocess path on Apo 1c)

Captured from `molass-researcher/experiments/13_rigorous_optimization/13g_rigorous_apo_1c.ipynb`,
the side-by-side comparison cell. The "subprocess" half of that run is
the regression target Phase 3 / Phase 4 are validated against.

| Metric | Subprocess (baseline) | In-process (Phase 3) |
|---|---|---|
| `best_fv` (logged in `callback.txt`) | −1.2656 | _TBD_ |
| `best_sv` (from logged `fv`) | 73.94 | _TBD_ |
| Parent re-eval `fv` (same params) | −1.4022 | _TBD_ |
| Parent re-eval SV | 78.24 | _TBD_ |
| ΔSV (parent − subprocess) | +4.30 | _TBD_ |
| Recovered Rg | _TBD_ | _TBD_ |
| Wall time (s) | ≈153 | _TBD_ |

Settings: Apo 2-component, `method='NS'`, `niter=30`, `clear_jobs=True`,
default trimming, linear baseline, no anomaly mask. Captured April 26, 2026
during the Fix #21 revert verification (commits `9d77a5e` → `b2ea136`).
The `mon_opt` instance built via `create_optimizer_from_job` reproduces the
subprocess `fv = −1.2656` exactly, confirming the divergence is structural
(disk-load vs library-prepared dsets) rather than stochastic.

## Phase 3 validation (split-architecture parity, Apo 2c)

Captured from `molass-researcher/experiments/13_rigorous_optimization/13h_split_architecture_validation.ipynb`,
running `compare_optimization_paths(decomp, rgcurve, method='NS', niter=20,
paths=('subprocess','in_process'), monitor=False)` on April 26, 2026
(molass-library commit `14edf7b`).

| Metric | Subprocess | In-process | Δ (in_process − subprocess) |
|---|---|---|---|
| `best_fv` | −1.4232 | −1.4022 | +0.0210 |
| `best_sv` | 78.85 | 78.24 | −0.60 |
| Rg[1] (Å) | 33.40 | 33.39 | −0.01 |
| Rg[2] (Å) | 33.23 | 32.91 | −0.31 |
| Wall time (s) | 1145.7 | 1295.4 | +149.8 |

Tolerance check (`assert_parity(fv_rtol=5e-2, sv_atol=2.0, rg_atol=1.0)`):
**PASS**. |Δfv|/|fv| = 1.5% (≪ 5%), |ΔSV| = 0.60 (≪ 2.0), max ΔRg = 0.31 Å
(< 1.0 Å). The two paths converge to numerically equivalent solutions; the
remaining drift is well within UltraNest stochasticity.

Wall-time gap (+13%) is the in-process slowdown previously diagnosed in
`13h` cell `[7c]` (≈3.5 ms/eval subprocess vs ≈15.6 ms/eval in-process).
The fv comparison eliminates *correctness* concerns about the in-process
path; the slowdown is now isolated as a pure optimization concern
(UltraNest / GIL / threading), to be addressed in Phase 5+.

## References

- #117 — Root-cause analysis: parent vs subprocess fv divergence
- #118 — Fix 1: `monitor_optimizer` indirection in `MplMonitor` (closed)
- #119 — Fix 2 (reopened): subprocess should optimize against library-prepared data
- Convention 9 in `molass-library/.github/copilot-instructions.md` — current
  documented behavior of the subprocess architecture
