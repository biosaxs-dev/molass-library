"""
    Guinier.RgCurveProcess.py

    The per-frame Rg curve in a separate process (molass-library#400).

    The Guinier loop of :meth:`~molass.DataObjects.SecSaxsData.get_rg_curve` is pure Python and
    keeps the GIL for a minute or more on ~1000 frames: in a GUI process every Tk/matplotlib draw
    is slowed down by an order of magnitude while it runs in a thread. :class:`RgCurveJob` runs it
    in a spawned child process instead:

    - the XR arrays reach the child through shared memory (read-only, not copied),
    - the child writes its running Rg values into a shared buffer, which the parent reads with
      :meth:`RgCurveJob.progress` (a live overlay, no per-frame messages),
    - the finished curve comes back through a queue and is picked up by :meth:`RgCurveJob.poll`,
      which never blocks and is meant to be called from a GUI timer.

    Start one with :meth:`~molass.DataObjects.SecSaxsData.start_rg_curve_process`. A script that
    starts a job must be importable without side effects (``if __name__ == "__main__":``), as for
    any ``spawn`` child; a frozen application must call ``multiprocessing.freeze_support()``.
"""
import multiprocessing
import os
import time

import numpy as np

_POLL_INTERVAL = 0.05


def _lower_priority():
    """Let the GUI process win when both want the CPU (replaces cooperative pausing)."""
    try:
        if os.name == "nt":
            import ctypes
            BELOW_NORMAL_PRIORITY_CLASS = 0x4000
            kernel32 = ctypes.windll.kernel32
            kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)
        else:
            os.nice(5)
    except Exception:
        pass


def _worker_main(xr_spec, progress_spec, queue, low_priority):
    """Entry point of the child process: send ``('done', RgCurve bundle)`` or ``('error', text)``."""
    try:
        if low_priority:
            _lower_priority()
        from molass.Global.ArrayBundle import ArrayBundle
        from molass.DataObjects.XrData import XrData
        from molass.Guinier.RgCurveUtils import compute_rgcurve_info
        from molass.Guinier.RgCurve import construct_rgcurve_from_list
        with ArrayBundle.attach(xr_spec) as xr_bundle, ArrayBundle.attach(progress_spec, readonly=False) as progress:
            xr = XrData.from_bundle(xr_bundle)
            rg_shared = progress["rg_buffer"]
            n_done = progress["n_done"]

            def progress_cb(rg_buffer, j):
                rg_shared[j] = rg_buffer[j]
                n_done[0] = j + 1

            rginfo = compute_rgcurve_info(xr, progress_cb=progress_cb)
            curve = construct_rgcurve_from_list(rginfo)
            result = curve.to_bundle()
            del xr, rg_shared, n_done, progress_cb
        queue.put(("done", result))
    except BaseException as exc:
        import traceback
        queue.put(("error", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"))


class RgCurveJob:
    """A running (or finished) Rg-curve computation in a child process.

    Create it with :meth:`SecSaxsData.start_rg_curve_process
    <molass.DataObjects.SecSaxsData.SecSaxsData.start_rg_curve_process>`. Use it as a context
    manager or call :meth:`close`: that releases the shared memory and stops a child still running.

    Attributes
    ----------
    n_frames : int
        Number of frames to fit.
    """

    def __init__(self, xr, on_done=None, low_priority=True):
        from molass.Global.ArrayBundle import ArrayBundle
        self.n_frames = int(xr.M.shape[1])
        self._on_done = on_done
        self._outcome = None
        self._last_progress = (0, np.zeros(self.n_frames))
        self._process = None
        self._shared = []
        self._queue = None
        try:
            xr_shared = xr.to_bundle().share()
            self._shared.append(xr_shared)
            progress_shared = ArrayBundle.zeros(
                {"rg_buffer": ((self.n_frames,), float), "n_done": ((1,), np.int64)}).share()
            self._shared.append(progress_shared)
            self._progress = progress_shared.bundle
            context = multiprocessing.get_context("spawn")
            self._queue = context.Queue()
            self._process = context.Process(
                target=_worker_main, args=(xr_shared.spec, progress_shared.spec, self._queue, low_priority),
                daemon=True)
            self._process.start()
        except BaseException:
            self._release()
            raise

    @classmethod
    def finished(cls, curve):
        """A job that is already done with ``curve`` (cached result: no child process)."""
        job = cls.__new__(cls)
        job.n_frames = len(curve.frames)
        job._on_done = None
        job._outcome = ("done", curve)
        job._last_progress = (job.n_frames, np.asarray(curve.rgs, dtype=float).copy())
        job._process = job._queue = None
        job._shared = []
        return job

    # -- state ------------------------------------------------------------------------------
    @property
    def done(self):
        """Whether the job has ended (successfully or not) and :meth:`poll` has noticed."""
        return self._outcome is not None

    def progress(self):
        """``(n_done, rg_buffer)``: frames fitted so far and a copy of the running Rg values
        (0 for frames not yet fitted). Cheap; safe to call from a GUI timer."""
        if self._outcome is None:
            n_done = int(self._progress["n_done"][0])
            self._last_progress = (n_done, self._progress["rg_buffer"].copy())
        return self._last_progress

    def poll(self):
        """Non-blocking: ``None`` while running, else the outcome (the same one on every later call):

        - ``('done', RgCurve)``
        - ``('error', text)`` -- the child failed or died
        - ``('cancelled', None)``
        """
        if self._outcome is not None:
            return self._outcome
        message = self._get_message()
        if message is None and not self._process.is_alive():
            message = self._get_message()       # a message may land just before the child exits
            if message is None:
                message = ("error", f"the Rg-curve process exited unexpectedly (exit code {self._process.exitcode})")
        if message is None:
            return None
        kind, payload = message
        if kind == "done":
            from molass.Guinier.RgCurve import RgCurve
            try:
                payload = RgCurve.from_bundle(payload)
            except Exception as exc:
                kind, payload = "error", f"{type(exc).__name__}: {exc}"
        self.progress()
        self._finish((kind, payload))
        if kind == "done" and self._on_done is not None:
            self._on_done(payload)
        return self._outcome

    def result(self, timeout=None):
        """Wait for the curve (blocking) and return it; ``RuntimeError`` if the job failed or was cancelled."""
        t0 = time.monotonic()
        while True:
            outcome = self.poll()
            if outcome is not None:
                break
            if timeout is not None and time.monotonic() - t0 > timeout:
                raise TimeoutError("the Rg curve is not ready")
            time.sleep(_POLL_INTERVAL)
        kind, payload = outcome
        if kind != "done":
            raise RuntimeError(f"Rg-curve job {kind}: {payload}")
        return payload

    def cancel(self):
        """Stop the child and release the shared memory; ``poll()`` then returns ``('cancelled', None)``."""
        if self._outcome is None:
            self.progress()
            self._finish(("cancelled", None))

    def close(self):
        """Release everything; cancels a job that is still running."""
        self.cancel()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- internals --------------------------------------------------------------------------
    def _get_message(self):
        import queue
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def _finish(self, outcome):
        self._outcome = outcome
        self._release()

    def _release(self):
        process, self._process = self._process, None
        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=10)
        q, self._queue = self._queue, None
        if q is not None:
            q.close()
            q.cancel_join_thread()
        self._progress = None
        shared, self._shared = self._shared, []
        for item in shared:
            item.close()

    def __del__(self):
        try:
            if getattr(self, "_shared", None):
                self._release()
        except Exception:
            pass

    def __repr__(self):
        state = "running" if self._outcome is None else self._outcome[0]
        return f"RgCurveJob({state}, {self.n_frames} frames)"
