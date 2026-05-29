## Summary

`optimize_rigorously(method='CMA', in_process=True, async_=True)` (the default async mode) crashes the Jupyter kernel with **STATUS_ACCESS_VIOLATION (0xC0000005)** on Python 3.14 / Windows.

## Environment

- Python 3.14.4 (Windows)
- molass-library v0.9.8
- cma v4.4.4 (pure Python)
- IPython / ipykernel (Jupyter notebook)

## Reproduction

```python
run = decomp.optimize_rigorously(
    analysis_folder='temp',
    method='CMA',
    niter=5,
    in_process=True,
    # async_=True is the default
)
# cell returns → kernel crashes with STATUS_ACCESS_VIOLATION
```

## Investigation (`21c_cma_inprocess_repro.ipynb`)

Tier-by-tier isolation identified the root cause:

| Test | Config | Main-thread state | Result |
|------|--------|-------------------|--------|
| [5] | `optimize_rigorously(async_=True)`, cell returns | IPython asyncio event loop | **CRASH** |
| [7] | `optimizer.solve('cma')` in daemon thread | Main cell alive (blocking) | OK |
| [8] | `run_optimizer_in_process` from main thread | Blocking | OK |
| [9] | `run_optimizer_in_process` from daemon, main blocking | Main cell alive (blocking) | OK |
| [10] | `optimize_rigorously(async_=False)` | Main thread blocked | OK |
| [11] | `optimize_rigorously(async_=True)` + cell blocks on join loop | Main cell alive (blocking) | OK |

**Root cause**: Crash requires BOTH conditions simultaneously:
1. Optimizer's inner `_solve_thread` (daemon) running NumPy BLAS (GIL released)
2. IPython's asyncio event loop running on main thread (only active after cell returns)

**What the crash is NOT**: CMA C code (CMA is pure Python), the objective function alone, `solve()` in a daemon thread, or `load_best()`/`live_status()`.

**Suspected mechanism**: IPython's ProactorEventLoop (Windows IOCP) running concurrently with a NumPy BLAS daemon thread causes a STATUS_ACCESS_VIOLATION. This may be specific to Python 3.14's C implementation of asyncio / IOCP.

## Proposed Fix (short-term)

In `make_rigorous_decomposition_impl` (or `optimize_rigorously`), when `in_process=True` and `async_=True`, automatically fall back to `async_=False` and emit a `UserWarning`:

```python
if in_process and async_ and method in ('CMA', 'ultranest'):
    import warnings
    warnings.warn(
        "optimize_rigorously(in_process=True, async_=True) is not supported on "
        "Windows/Python 3.14 for CMA/NS — falling back to async_=False.",
        UserWarning, stacklevel=3
    )
    async_ = False
```

## Longer-term Fix

Replace `threading.Thread(target=_run_in_process, daemon=True)` with
`asyncio.ensure_future(loop.run_in_executor(None, _run_in_process))` to integrate the
background work with IPython's event loop rather than running as an independent daemon thread.

## Related

- #138 (NS in_process crash — same pattern, different solver)
- molass-legacy#26 (kernel restart safety fix for in_process path)
- Investigation notebook: `molass-researcher/experiments/21_rigorous_solvers/21c_cma_inprocess_repro.ipynb`
