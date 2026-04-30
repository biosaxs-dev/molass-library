# Design Discussion: Terminate Job for In-Process Runs

**Status**: Draft — open for discussion  
**Related**: molass-library#139 (Phase 2, where Terminate was hidden)  
**Date**: April 28, 2026

---

## Current state

The Terminate Job button is hidden when `MplMonitor` is driven by a `_RunInfoSource`
(i.e. `optimize_rigorously(in_process=True, async_=True)`).  The reason given at the
time of Phase 2 was:

> "Resume and Terminate are not meaningful for thread-based runs:  
> niter is fixed and threads cannot be killed cleanly."

`_RunInfoSource.terminate()` is therefore a no-op:

```python
# molass_legacy/Optimizer/MplMonitor.py
class _RunInfoSource:
    def terminate(self):
        """No-op: cannot cleanly kill a Python thread."""
        pass
```

The `terminate_event` on `MplMonitor` is already checked in the watch loop and
wired to `source.terminate()` — so the infrastructure is ready.  The missing piece
is a live signal path from `terminate_event` → the optimizer thread.

---

## Why it matters

A BH run with `niter=200` at ~2–3 min/step takes 6–10 hours.  If the user decides
after 30 minutes that the result is already good enough (e.g. `best_sv > 80`), there
is no way to stop the optimizer short of **restarting the kernel** — which destroys
the live `RunInfo` object and any in-memory state.

The dashboard shows a "Completed" status only when all `niter` steps finish.  No
early-exit mechanism exists.

---

## What already exists

| Component | Where | Role |
|-----------|-------|------|
| `terminate_event` | `MplMonitor` | `threading.Event`; set by Terminate button / `monitor.terminate()` |
| Watch-loop check | `MplMonitor.watch_progress` L770 | calls `self.source.terminate()` when event is set |
| GIL-release loop | `InProcessRunner.py` / molass-legacy#26 | main thread polls `thread.join(0.05)` → Ctrl+C lands cleanly |
| BH callback param | `scipy.optimize.basinhopping` | accepts `callback(x, f, accepted)` → stops if returns `True` |

---

## The signal path that needs to be wired

```
User clicks "Terminate Job"
    → MplMonitor.trigger_terminate()
        → terminate_event.set()
            → watch thread calls _RunInfoSource.terminate()
                → ??? needs to reach optimizer.solve()
                    → BH callback checks event → returns True → BH stops
```

Currently the `???` link is broken: `_RunInfoSource.terminate()` is a no-op.

---

## Design options

### Option A — Cooperative flag via `terminate_event` passed to solver

**Mechanism**:

1. Store `terminate_event` on `RunInfo` (set by the monitor after construction, or
   passed in at construction time).
2. In `InProcessRunner.run_optimizer_in_process()`, pass a BH callback that checks it:

```python
# In InProcessRunner.py — BH callback
def _make_terminate_callback(event):
    def callback(x, f, accepted):
        if event is not None and event.is_set():
            return True   # signals BH to stop
        return False
    return callback
```

3. Pass this to `optimizer.solve()` → into `scipy.optimize.basinhopping(callback=...)`.
4. Update `_RunInfoSource.terminate()` to call `run_info.terminate_event.set()`.

**Pros**:
- Clean and safe — BH exits after the current step completes, no mid-step abort.
- No thread killing. No `ctypes`. No segfault risk.
- `callback.txt` is complete up to the last accepted step; `load_best()` works normally.
- The watch loop already handles `terminate_event` → no dashboard changes needed
  beyond re-showing the button.

**Cons**:
- Stop is not instant — the current BH step must finish first (~seconds for BH,
  potentially longer for a single NM sub-minimization).
- NS/MCMC/SMC need a method-specific hook; NS crashes with the full molass
  objective in_process=True (molass-library#138, still open — see Q5).
- Requires threading `terminate_event` through `InProcessRunner` → `BasicOptimizer.solve()`.

**Affected files**:
- `molass_legacy/Optimizer/InProcessRunner.py` — add callback factory, pass to `solve()`
- `molass_legacy/Optimizer/MplMonitor.py` — `_RunInfoSource.terminate()`: set event; re-show button for in-process
- `molass/Rigorous/RunInfo.py` — add `terminate_event` attribute; expose `set_terminate_event()`

---

### Option B — Show button disabled, with tooltip

**Mechanism**: Re-show the Terminate Job button but keep it disabled; set
`tooltip="Use Ctrl+C to stop an in-process run"`.

**Pros**: Zero implementation risk. Documents the limitation explicitly.

**Cons**: Still requires the user to restart the kernel if they want to stop.
`tooltip` is not reliably visible in VS Code's ipywidgets renderer.

---

### Option C — Thread interrupt via `ctypes.pythonapi.PyThreadState_SetAsyncExc`

Injects a `KeyboardInterrupt` into the optimizer thread from the main thread.

**Pros**: Stops "immediately" (on the next Python bytecode instruction).

**Cons**: Fragile in CPython; UB if the thread is in a C extension (e.g. inside
scipy's BFGS minimizer). Leaks memory if the thread holds C-level resources.  
Not recommended.

---

## Recommended approach: Option A

Option A is the natural completion of the cooperative-flag design already called out
in Issue #139 as "a future enhancement."  The key engineering constraints are:

1. **BH stop granularity**: BH calls its `callback` after each accepted step, not
   after each Nelder-Mead function evaluation.  A single NM sub-minimization on a
   large parameter vector can take tens of seconds, so "stop" means "stop at the
   next accepted step."  This is acceptable.

2. **NS / MCMC / SMC**: Need method-specific hooks.
   - **UltraNest** (`NS`): UltraNest itself is thread-safe (verified in
     `13v_ultranest_inprocess_repro.ipynb` with a trivial objective), but the full
     molass objective crashes with ExitCode 0xC0000005 (access violation in
     molass-legacy C/Cython code) when run in the NS thread.  Issue #138 remains
     open.  NS is blocked for `in_process=True` until the objective thread-safety
     is confirmed.  `in_process=False` (subprocess) is the safe path for NS.
   - MCMC (emcee): Can check event between chain steps — add to the emcee progress
     callback.
   - SMC: TBD.

3. **Thread safety**: `threading.Event.set()` / `is_set()` are already thread-safe.

---

## Implementation sketch (BH path only)

### Step 1 — `RunInfo.py`: add `terminate_event`

```python
def __init__(self, ...):
    ...
    self._terminate_event = None   # set by monitor via set_terminate_event()

def set_terminate_event(self, event):
    """Called by MplMonitor after construction to wire the cooperative stop flag."""
    self._terminate_event = event

@property
def terminate_event(self):
    return self._terminate_event
```

### Step 2 — `InProcessRunner.py`: pass terminate callback to `solve()`

```python
def run_optimizer_in_process(..., terminate_event=None, ...):
    ...
    bh_callback = None
    if terminate_event is not None:
        def bh_callback(x, f, accepted):
            return terminate_event.is_set()

    result, work_folder = optimizer.solve(
        ...,
        callback=bh_callback,   # new kwarg — only used by BH path
    )
```

### Step 3 — `BasicOptimizer.solve()` (molass-legacy): forward `callback` to BH

```python
# In SolverBH.py or equivalent
scipy.optimize.basinhopping(..., callback=callback)
```

### Step 4 — `_RunInfoSource.terminate()`: set the event

```python
def terminate(self):
    event = self._ri.terminate_event
    if event is not None:
        event.set()
```

### Step 5 — `MplMonitor.create_dashboard()`: re-show Terminate for in-process

```python
if in_process:
    controls_children = [self.status_label,
                          self.space_label2,
                          self.terminate_button,   # re-shown
                          self.space_label3,
                          self.export_button]
```

### Step 6 — Wire event in `for_run_info()` / `optimize_rigorously()`

```python
# After constructing MplMonitor and RunInfo:
run_info.set_terminate_event(monitor.terminate_event)
```

---

## Open questions

1. **Event ownership**: Should `terminate_event` be created by `RunInfo` (and passed
   to `MplMonitor`) or created by `MplMonitor` (and passed to `RunInfo`)?  
   Current default: `MplMonitor` creates it in `create_dashboard()`.  
   Simpler alternative: `RunInfo` creates it at construction; `MplMonitor` uses it
   directly from `run_info.terminate_event`.

2. **Re-show Resume too?** Resume is also hidden for in-process.  With cooperative
   termination, "stop early + resume from best" becomes a natural workflow.  However,
   `run_impl` for in-process starts a new thread — it would need to be called from
   the watch thread or a separate thread, not the ipywidgets callback thread.  Defer.

3. **Status label after cooperative stop**: Should the dashboard show "Status:
   Stopped" (distinct from "Completed") so the user knows BH was cut short?

4. **`load_first()` / `load_best()` compatibility**: After a cooperative stop,
   `callback.txt` is complete up to the last accepted step.  `load_best()` and
   `load_first()` require no changes.

5. **NS path**: UltraNest itself is thread-safe (13v), but the full molass
   objective crashes in the NS thread (molass-library#138, still open).  Show the
   Terminate button only when `method='BH'` for now.  For NS/MCMC/SMC, either hide
   the button or disable it with a tooltip explaining the limitation.  Revisit once
   #138 is resolved.

---

## Proposed next step

Implement Option A for the BH path only.  Open a molass-legacy issue tracking
Steps 2–4, and a molass-library issue for Steps 1 and 6.
NS cooperative stop is blocked until #138 (NS in-process crash with full molass
objective) is resolved.  MCMC/SMC tracked as a separate follow-up.
