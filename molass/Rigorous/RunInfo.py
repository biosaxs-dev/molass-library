"""
Rigorous.RunInfo.py
"""

class RunInfo:
    """Handle returned by :func:`molass.Rigorous.make_rigorous_decomposition`
    (and ``Decomposition.optimize_rigorously()``).

    Attributes
    ----------
    ssd : SecSaxsData
        The SEC-SAXS dataset used for the optimization.
    optimizer : Optimizer
        The in-process optimizer object.  Only populated for the in-process
        path (``in_process=True``); ``None`` for the subprocess path.
    dsets : list
        Dataset objects passed to the optimizer.
    init_params : ndarray
        Initial parameter vector used to start the optimization.
    monitor : MplMonitor or None
        Live monitor object for the subprocess path; ``None`` for in-process.
    analysis_folder : str or None
        Root folder for all optimizer output.  Set this if you want the
        progress/sidecar helpers to work without arguments.
    decomposition : Decomposition or None
        The ``Decomposition`` object that launched this run.
    work_folder : str or None
        Absolute path to the job folder written by the in-process optimizer
        (``<analysis_folder>/optimized/jobs/000`` or similar).  Set only for
        the in-process path; ``None`` for the subprocess path.  Contains
        ``init_params.txt``, ``callback.txt``, etc.
    in_process_result : object or None
        Raw result object returned by ``run_optimizer_in_process()``.
        Set only for the in-process path.
    """

    def __init__(self, ssd, optimizer, dsets, init_params, monitor=None,
                 analysis_folder=None, decomposition=None, rgcurve=None):
        self.ssd = ssd
        self.optimizer = optimizer
        self.dsets = dsets
        self.init_params = init_params
        self.monitor = monitor
        self.analysis_folder = analysis_folder
        self.decomposition = decomposition
        self.rgcurve = rgcurve          # cached to avoid recomputation in load_best/load_first
        # Set by RigorousImplement for in_process=True runs:
        self.work_folder = None
        self.in_process_result = None
        # Set by RigorousImplement when async_=True:
        self._async_thread = None
        self._async_error = None

    @property
    def is_alive(self):
        """``True`` while an async background thread is running, ``False`` when done.

        Always ``False`` for synchronous (blocking) runs.
        Check this after ``optimize_rigorously(async_=True)`` to know when
        it is safe to call :meth:`load_best` or :meth:`live_status`.
        """
        t = self._async_thread
        if t is None:
            return False
        return t.is_alive()

    def __repr__(self):
        if self._async_thread is not None:
            state = "running" if self._async_thread.is_alive() else "done"
        else:
            state = "done"
        parts = [f"state={state!r}"]
        if self.analysis_folder is not None:
            try:
                from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs
                jobs = list_rigorous_jobs(self.analysis_folder)
                if jobs:
                    import math
                    best_fv = min(j.best_fv for j in jobs)
                    best_sv = -200 / (1 + math.exp(-1.5 * best_fv)) + 100
                    n_evals = sum(j.iterations for j in jobs)
                    parts.append(f"n_evals={n_evals}")
                    parts.append(f"best_sv={best_sv:.1f}")
            except Exception:
                pass
        return f"RunInfo({', '.join(parts)})"

    def get_current_decomposition(self, **kwargs):
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.Rigorous.CurrentStateUtils
            reload(molass.Rigorous.CurrentStateUtils)
        from molass.Rigorous.CurrentStateUtils import construct_decomposition_from_results
        return construct_decomposition_from_results(self, **kwargs)

    def resume(self, niter=20, debug=True):
        """Resume optimization from the best parameters of the previous run.

        This mirrors the legacy GUI's "Resume" button: extracts the best
        parameters from the completed job's callback.txt, then launches a
        new optimizer subprocess using those as the starting point.

        Parameters
        ----------
        niter : int, optional
            Number of iterations for the resumed optimization. Default is 20.
        debug : bool, optional
            If True, enable debug mode (reloads modules from disk). Default is True.

        Returns
        -------
        self : RunInfo
            The same RunInfo instance, updated with the new monitor.
        """
        import os
        from molass_legacy._MOLASS.SerialSettings import get_setting
        from molass_legacy.Optimizer.Scripting import get_params, run_optimizer

        # Terminate the old monitor if still running
        if self.monitor is not None:
            try:
                self.monitor.terminate()
            except Exception:
                pass

        # Get best params from the latest job's callback.txt (reads from disk)
        optimizer_folder = get_setting('optimizer_folder')
        jobs_folder = os.path.join(optimizer_folder, "jobs")
        jobids = sorted(d for d in os.listdir(jobs_folder)
                        if os.path.isdir(os.path.join(jobs_folder, d)))
        last_job_folder = os.path.join(jobs_folder, jobids[-1])
        best_params = get_params(last_job_folder, debug=debug)

        # Re-prepare the optimizer with the best params
        self.optimizer.prepare_for_optimization(best_params)

        # Run a new optimization (clear_jobs=False to preserve previous jobs)
        x_shifts = self.dsets.get_x_shifts()
        monitor = run_optimizer(self.optimizer, best_params, niter=niter,
                                clear_jobs=False, x_shifts=x_shifts, debug=debug)

        self.monitor = monitor
        self.init_params = best_params
        return self

    def wait(self, timeout=600, poll_interval=5):
        """Wait for rigorous optimization results to become available.

        Parameters
        ----------
        timeout : float, optional
            Maximum seconds to wait (default 600). Use ``0`` for no limit.
        poll_interval : float, optional
            Seconds between checks (default 5).

            .. note::
                For async in-process runs (``async_=True``), ``poll_interval``
                is **silently ignored** — the implementation calls
                ``thread.join(timeout)`` once with no looping.

        Returns
        -------
        bool
            ``True`` if results appeared, ``False`` if timed out.

        Raises
        ------
        ValueError
            If no ``analysis_folder`` was stored (e.g. RunInfo was created
            without one).

        .. warning:: **Async in-process path** (``async_=True``)

            This method calls ``_async_thread.join(timeout)`` once, which has
            two failure modes for long BH/NS runs:

            - **Default** ``timeout=600``: silently returns ``False`` for runs
              longer than 10 minutes while the optimizer is still running.
              Downstream calls to ``load_best()`` will then fail or load stale
              results.
            - ``timeout=0`` **(no limit)**: blocks the kernel's main thread
              entirely.  No other cell — including ``live_status()``,
              ``is_alive``, or any monitoring probe — can execute until the
              optimizer finishes.

            For interactive notebooks prefer :meth:`load_first`, which waits
            only until the *first* result lands on disk and returns
            immediately, or poll manually with::

                if run_info.is_alive:
                    print(run_info.live_status())
        """
        # For async in-process runs, join the background thread directly.
        if self._async_thread is not None:
            self._async_thread.join(timeout=timeout if timeout else None)
            if self._async_error is not None:
                raise RuntimeError("Async optimizer failed") from self._async_error
            return not self._async_thread.is_alive()

        if self.analysis_folder is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )
        from molass.Rigorous.CurrentStateUtils import wait_for_rigorous_results
        return wait_for_rigorous_results(
            self.analysis_folder, timeout=timeout, poll_interval=poll_interval
        )

    def load_best(self, debug=False):
        """Load the best rigorous optimization result.

        Combines ``list_rigorous_jobs()`` and ``load_rigorous_result()``
        into one call: finds the job with the lowest objective function
        value and reconstructs the ``Decomposition`` from it.

        Parameters
        ----------
        debug : bool, optional
            If True, reload modules from disk.

        Returns
        -------
        Decomposition
            A Decomposition built from the best optimized parameters.

        Raises
        ------
        ValueError
            If no ``analysis_folder`` was stored.
        FileNotFoundError
            If no completed jobs are found.

        See Also
        --------
        get_score_breakdown : Inspect the individual score and penalty
            components that make up the objective value (fv).

        Examples
        --------
        ::

            run_info = decomp.optimize_rigorously(
                analysis_folder="temp_analysis", niter=30)
            run_info.wait(timeout=600)
            result = run_info.load_best()
            result.plot_components()
        """
        if self.analysis_folder is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )
        from molass.Rigorous.CurrentStateUtils import (
            list_rigorous_jobs, load_rigorous_result,
        )
        jobs = list_rigorous_jobs(self.analysis_folder)
        if not jobs:
            raise FileNotFoundError(
                f"No completed jobs found in {self.analysis_folder}"
            )
        best = min(jobs, key=lambda j: j.best_fv)
        decomp = self.decomposition
        if decomp is None:
            raise ValueError(
                "No decomposition stored in this RunInfo. "
                "Cannot reconstruct result without the initial decomposition."
            )
        return load_rigorous_result(
            decomp, self.analysis_folder, jobid=best.id,
            rgcurve=self.rgcurve, debug=debug
        )

    def load_first(self, timeout=0, poll_interval=5, debug=False):
        """Wait for the first rigorous result, then load the best job found so far.

        Combines :func:`wait_for_rigorous_results` and :meth:`load_best` in
        one call.  Safe to run immediately after firing the optimizer with
        ``async_=True`` — there is no need to check ``is_alive`` or call
        ``wait()`` first.

        Parameters
        ----------
        timeout : float, optional
            Maximum seconds to wait for the first result (default ``0`` = no
            limit).  When non-zero and no result appears within ``timeout``
            seconds, raises :class:`TimeoutError`.
        poll_interval : float, optional
            Seconds between filesystem checks (default 5).
        debug : bool, optional
            If True, reload modules from disk.

        Returns
        -------
        Decomposition
            A Decomposition built from the best optimized parameters available
            at the time the first result lands on disk.

        Raises
        ------
        TimeoutError
            If ``timeout > 0`` and no result appears within that time.

        Notes
        -----
        Interrupt with **Ctrl+C** to cancel the wait at any time.

        If the optimizer is still running when ``load_first()`` returns, the
        result reflects only the jobs completed so far — not the final best.
        Re-call :meth:`load_best` after the run finishes to get the true
        global best.

        Examples
        --------
        ::

            run_info = decomp.optimize_rigorously(
                rgcurve, method='BH', niter=200,
                analysis_folder="temp_analysis",
                async_=True,
            )
            # Safe to call immediately — blocks until first BH step is on disk:
            result = run_info.load_first()
            result.plot_components()
        """
        from molass.Rigorous.CurrentStateUtils import wait_for_rigorous_results
        ready = wait_for_rigorous_results(
            self.analysis_folder,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        if not ready:
            raise TimeoutError(
                f"No rigorous results appeared within {timeout}s "
                f"in {self.analysis_folder}"
            )
        return self.load_best(debug=debug)

    def get_score_breakdown(self, jobid=None, debug=False):
        """Evaluate the objective function and return individual score components.

        Loads the best (or specified) optimized parameters from disk, runs them
        through the optimizer's objective function, and returns a dict mapping
        each score name to its value.

        Score architecture
        ------------------
        The objective value ``fv`` is computed as::

            fv = synthesize(scores, positive_elevate=3) + sum(penalties)

        **Synthesized scores** (first 7): XR_2D_fitting, XR_LRF_residual,
        UV_2D_fitting, UV_LRF_residual, Guinier_deviation,
        Kratky_smoothness, SEC_conformance.  These are combined via a
        weighted RMS + spread measure, shifted so that a raw score of -3
        maps to zero contribution.

        **Additive penalties** (remaining entries): mapping_penalty,
        negative_penalty, baseline_penalty, outofbounds_penalty,
        order_penalty, control_penalty, consistency_penalty.  These are
        added directly to fv after synthesis.  A penalty of 1.0 raises
        fv by exactly 1.0.

        Parameters
        ----------
        jobid : str, optional
            Specific job id to evaluate. If None, uses the best job
            (lowest ``best_fv``).
        debug : bool, optional
            If True, reload modules from disk.

        Returns
        -------
        dict
            ``{'fv': float, 'scores': {name: value, ...}}`` where ``scores``
            maps each score/penalty name to its numeric value.

        Raises
        ------
        ValueError
            If no ``analysis_folder`` was stored.
        FileNotFoundError
            If no completed jobs are found.

        Examples
        --------
        ::

            run_info = decomp.optimize_rigorously(
                analysis_folder="temp_analysis", niter=30)
            run_info.wait()
            breakdown = run_info.get_score_breakdown()
            for name, val in breakdown['scores'].items():
                print(f"{name}: {val:.4f}")
        """
        import os
        from molass_legacy.Optimizer.Scripting import get_params

        if self.analysis_folder is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )

        optimizer_folder = os.path.join(
            os.path.abspath(self.analysis_folder), "optimized"
        )
        jobs_folder = os.path.join(optimizer_folder, "jobs")

        if jobid is None:
            from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs
            jobs = list_rigorous_jobs(self.analysis_folder)
            if not jobs:
                raise FileNotFoundError(
                    f"No completed jobs found in {self.analysis_folder}"
                )
            best = min(jobs, key=lambda j: j.best_fv)
            jobid = best.id

        job_folder = os.path.join(jobs_folder, jobid)
        params = get_params(job_folder, debug=debug)

        result = self.optimizer.objective_func(params, return_full=True)
        fv = result[0]
        score_array = result[1]
        names = self.optimizer.get_score_names()

        scores = {}
        for name, val in zip(names, score_array):
            scores[name] = float(val)

        return {'fv': float(fv), 'scores': scores}

    def get_current_curves(self):
        """Return the data and model curves currently shown on the monitor.

        Delegates to ``MplMonitor.get_current_curves()`` (molass-legacy #31,
        **monitor readability**).  Provides a single-call entry point from
        the user-facing ``RunInfo`` object so that an AI agent can query
        ``run_info.get_current_curves()`` without knowing about the internal
        monitor attribute.

        Returns
        -------
        dict or None
            See ``MplMonitor.get_current_curves()`` for the full key list.
            Returns ``None`` if the monitor is not set or has no data yet.
        """
        if self.monitor is None:
            return None
        return self.monitor.get_current_curves()

    def diagnose(self, breakdown=None):
        """Map score values to physical interpretations.

        Calls ``get_score_breakdown()`` if no breakdown is provided, then
        applies encoded rules to each score/score-pair and returns a list of
        ``Diagnosis`` namedtuples with structured physical meaning.

        This allows an AI agent (or a human) to understand *why* a fit is poor
        without requiring domain knowledge: the rules encode the mapping from
        numeric scores to physical causes.

        Parameters
        ----------
        breakdown : dict, optional
            Output of ``get_score_breakdown()``.  If None, it is computed
            automatically (which loads and evaluates the best job from disk).

        Returns
        -------
        list of Diagnosis
            Each ``Diagnosis`` has the fields:
            - ``score`` : str -- the score/penalty name (or pair)
            - ``status`` : str -- ``'good'``, ``'fair'``, ``'poor'``, or
              ``'failing'``
            - ``reason`` : str -- human-readable explanation
            - ``suggestion`` : str or None -- recommended next diagnostic step

        Examples
        --------
        ::

            run_info.wait()
            for d in run_info.diagnose():
                print(f"[{d.status.upper()}] {d.score}: {d.reason}")
                if d.suggestion:
                    print(f"  -> {d.suggestion}")
        """
        from collections import namedtuple

        Diagnosis = namedtuple('Diagnosis', ['score', 'status', 'reason', 'suggestion'])

        if breakdown is None:
            breakdown = self.get_score_breakdown()

        scores = breakdown['scores']
        result = []

        # --- Helper -------------------------------------------------------
        def _status_from_val(val, thresholds):
            # thresholds: list of (threshold, status) in order good -> failing
            # val is negative (lower is better); thresholds are negative
            # e.g. [(-1.0, 'good'), (-0.5, 'fair'), (-0.3, 'poor')]
            for threshold, status in thresholds:
                if val <= threshold:
                    return status
            return thresholds[-1][1]

        # --- UV_LRF_residual ----------------------------------------------
        uv_lrf = scores.get('UV_LRF_residual')
        if uv_lrf is not None:
            if uv_lrf > -0.1:
                result.append(Diagnosis(
                    score='UV_LRF_residual',
                    status='failing',
                    reason=(
                        f"UV_LRF_residual = {uv_lrf:.3f} (near zero): the low-rank "
                        "factorization cannot fit the UV data matrix at all. This "
                        "usually means the UV model is completely misaligned with the data."
                    ),
                    suggestion="Call run_info.get_current_curves() to inspect UV data vs model peak positions.",
                ))
            elif uv_lrf > -0.3:
                result.append(Diagnosis(
                    score='UV_LRF_residual',
                    status='poor',
                    reason=(
                        f"UV_LRF_residual = {uv_lrf:.3f}: the low-rank residual "
                        "is poor, indicating a significant UV model misfit."
                    ),
                    suggestion="Call run_info.get_current_curves() to inspect UV data vs model curves.",
                ))
            elif uv_lrf > -0.7:
                result.append(Diagnosis(
                    score='UV_LRF_residual',
                    status='fair',
                    reason=f"UV_LRF_residual = {uv_lrf:.3f}: moderate UV low-rank residual.",
                    suggestion=None,
                ))

        # --- UV vs XR 2D fitting ratio ------------------------------------
        uv_2d = scores.get('UV_2D_fitting')
        xr_2d = scores.get('XR_2D_fitting')
        if uv_2d is not None and xr_2d is not None and xr_2d < 0 and uv_2d < 0:
            # Both scores are negative; larger magnitude = better.
            # ratio = UV/XR: close to 1 means similar quality; close to 0 means UV much worse.
            ratio = uv_2d / xr_2d
            if ratio < 0.33:
                result.append(Diagnosis(
                    score='UV_2D_fitting vs XR_2D_fitting',
                    status='poor',
                    reason=(
                        f"UV_2D_fitting ({uv_2d:.3f}) is {xr_2d/uv_2d:.1f}x worse than "
                        f"XR_2D_fitting ({xr_2d:.3f}): the UV 2D fit is disproportionately "
                        "bad compared to XR, suggesting the UV model components are "
                        "misaligned with the data while XR converged correctly."
                    ),
                    suggestion="Call run_info.get_current_curves() to compare UV data vs model peak positions.",
                ))
            elif ratio < 0.67:
                result.append(Diagnosis(
                    score='UV_2D_fitting vs XR_2D_fitting',
                    status='fair',
                    reason=(
                        f"UV_2D_fitting ({uv_2d:.3f}) is noticeably worse than "
                        f"XR_2D_fitting ({xr_2d:.3f})."
                    ),
                    suggestion=None,
                ))

        # --- UV_2D_fitting absolute ----------------------------------------
        if uv_2d is not None and uv_2d > -0.3:
            if not any(d.score == 'UV_2D_fitting vs XR_2D_fitting' for d in result):
                result.append(Diagnosis(
                    score='UV_2D_fitting',
                    status='poor',
                    reason=f"UV_2D_fitting = {uv_2d:.3f}: poor UV 2D fit.",
                    suggestion="Call run_info.get_current_curves() to inspect UV data vs model.",
                ))

        # --- Guinier_deviation --------------------------------------------
        guinier = scores.get('Guinier_deviation')
        if guinier is not None:
            if guinier > -0.3:
                result.append(Diagnosis(
                    score='Guinier_deviation',
                    status='poor',
                    reason=(
                        f"Guinier_deviation = {guinier:.3f}: poor Rg consistency "
                        "across elution frames. The decomposed components may not "
                        "represent physically distinct species."
                    ),
                    suggestion="Inspect decomp.get_rgs() and check if Rg values are stable across elution.",
                ))
            elif guinier > -0.7:
                result.append(Diagnosis(
                    score='Guinier_deviation',
                    status='fair',
                    reason=f"Guinier_deviation = {guinier:.3f}: moderate Rg consistency.",
                    suggestion=None,
                ))

        # --- SEC_conformance ----------------------------------------------
        sec = scores.get('SEC_conformance')
        if sec is not None and sec > -0.2:
            result.append(Diagnosis(
                score='SEC_conformance',
                status='poor',
                reason=(
                    f"SEC_conformance = {sec:.3f}: the elution curve shape does not "
                    "conform well to the SEC column model."
                ),
                suggestion=None,
            ))

        # --- Penalties ----------------------------------------------------
        penalty_names = [
            'mapping_penalty', 'negative_penalty', 'baseline_penalty',
            'outofbounds_penalty', 'order_penalty', 'control_penalty',
            'consistency_penalty',
        ]
        for pname in penalty_names:
            pval = scores.get(pname)
            if pval is not None and pval > 0.1:
                result.append(Diagnosis(
                    score=pname,
                    status='poor',
                    reason=(
                        f"{pname} = {pval:.3f}: a physical constraint is violated "
                        "(penalty > 0.1 raises fv directly)."
                    ),
                    suggestion=None,
                ))

        # --- All good ------------------------------------------------------
        if not result:
            result.append(Diagnosis(
                score='overall',
                status='good',
                reason="No significant issues detected in any score or penalty.",
                suggestion=None,
            ))

        return result

    @property
    def monitor_snapshot_json_path(self):
        """Path to the MplMonitor JSON sidecar written during the last run.

        The file is created when ``MOLASS_MONITOR_SNAPSHOT=1`` and exists at
        ``<analysis_folder>/optimized/figs/mplmonitor_latest.json``.

        Returns
        -------
        str
            Absolute path to the JSON file, whether or not it exists.
        None
            If ``analysis_folder`` was not set on this RunInfo.
        """
        import os
        if self.analysis_folder is None:
            return None
        return os.path.join(
            os.path.abspath(self.analysis_folder),
            "optimized", "figs", "mplmonitor_latest.json",
        )

    def check_progress(self, label=None, write_snapshot=False):
        """Read callback.txt(s) from all jobs and report best SV so far.

        Re-runnable at any time while the optimizer is running or after it
        completes.  Does not require the optimizer to have finished.

        The implementation lives in
        :func:`molass.Rigorous.CurrentStateUtils.check_progress` so it can
        be updated and reloaded without restarting the kernel — just call
        ``importlib.reload(molass.Rigorous.CurrentStateUtils)`` and the
        next invocation picks up the new logic automatically.

        Parameters
        ----------
        label : str, optional
            Display label prefix. Defaults to the analysis folder basename.
        write_snapshot : bool, optional
            If ``True``, write a compact JSON file to
            ``<analysis_folder>/optimized/progress_snapshot.json`` in addition
            to printing.  Read back via :meth:`load_progress_snapshot`.
            Default ``False``.

        Returns
        -------
        dict or None
            Progress data dict when there are evaluations to report; ``None``
            otherwise.

        Examples
        --------
        ::

            _run_sub.check_progress()                         # print only
            _run_sub.check_progress(label="subprocess")       # explicit label
            snap = _run_sub.check_progress(write_snapshot=True)  # persist + return

        See Also
        --------
        molass.Rigorous.check_progress : standalone form; also accepts a plain
            folder-path string when no ``RunInfo`` instance is at hand::

                from molass.Rigorous import check_progress
                check_progress("/path/to/analysis_folder")
        """
        from molass.Rigorous.CurrentStateUtils import check_progress as _impl
        return _impl(self, label=label, write_snapshot=write_snapshot)

    @property
    def progress_snapshot_json_path(self):
        """Path to the progress snapshot JSON written by ``check_progress(write_snapshot=True)``.

        Exists at ``<analysis_folder>/optimized/progress_snapshot.json``.

        Returns
        -------
        str
            Absolute path to the JSON file, whether or not it exists yet.
        None
            If ``analysis_folder`` was not set on this RunInfo.
        """
        import os
        if self.analysis_folder is None:
            return None
        return os.path.join(
            os.path.abspath(self.analysis_folder),
            "optimized", "progress_snapshot.json",
        )

    def load_progress_snapshot(self):
        """Load and return the progress snapshot JSON as a dict.

        Written by :meth:`check_progress` when ``write_snapshot=True``.
        Readable from any session — including a new AI session — without
        re-running the optimizer.

        Returns
        -------
        dict
            Keys: ``label``, ``n_evals``, ``best_fv``, ``best_sv``,
            ``sv_best_so_far``, ``timestamp``.

        Raises
        ------
        FileNotFoundError
            If the snapshot does not exist yet (call
            ``check_progress(write_snapshot=True)`` first).
        ValueError
            If ``analysis_folder`` is not set on this RunInfo.

        Examples
        --------
        ::

            _run_sub.check_progress(write_snapshot=True)
            snap = _run_sub.load_progress_snapshot()
            print(f"best SV: {snap['best_sv']:.2f}")
        """
        import json, os
        path = self.progress_snapshot_json_path
        if path is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Progress snapshot not found: {path}\n"
                "Call check_progress(write_snapshot=True) first."
            )
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def load_monitor_snapshot(self):
        """Load and return the MplMonitor JSON sidecar as a dict.

        Returns
        -------
        dict
            Parsed JSON content.

        Raises
        ------
        FileNotFoundError
            If the sidecar does not exist (``MOLASS_MONITOR_SNAPSHOT`` was not
            set, or the optimizer has not run yet).
        ValueError
            If ``analysis_folder`` is not set on this RunInfo.
        """
        import json, os
        path = self.monitor_snapshot_json_path
        if path is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"MplMonitor JSON sidecar not found: {path}\n"
                "Set MOLASS_MONITOR_SNAPSHOT=1 before running optimize_rigorously()."
            )
        with open(path) as fh:
            return json.load(fh)

    @property
    def sv_history(self):
        """Min-so-far SV trajectory from all ``callback.txt`` files.

        Returns the full sequence of best-SV-so-far values, one per accepted
        optimizer evaluation.  Readable at any time — while the run is in
        progress or after it completes.

        Returns
        -------
        list of float
            Running-minimum SV values.  ``sv_history[-1]`` is the best
            accepted SV of the entire run.  Empty list if no evaluations
            have been recorded yet.

        Raises
        ------
        ValueError
            If ``analysis_folder`` is not set on this RunInfo.

        Examples
        --------
        ::

            svs = run_sub.sv_history
            print(f"best SV: {svs[-1]:.2f}  start SV: {svs[0]:.2f}")
        """
        if self.analysis_folder is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )
        from molass.Rigorous.CurrentStateUtils import parse_sv_history
        return parse_sv_history(self.analysis_folder)

    def plot_sv_history(self, title=None, figsize=(8, 4)):
        """Plot the min-so-far SV trajectory from ``callback.txt``.

        One-liner convergence view.  Works at any time after at least one
        evaluation has been accepted.

        Parameters
        ----------
        title : str, optional
            Figure title.  Defaults to ``"SV history — <folder basename>"``.
        figsize : tuple, optional
            Matplotlib figure size.  Default ``(8, 4)``.

        Returns
        -------
        None

        Examples
        --------
        ::

            run_sub.plot_sv_history()
            run_sub.plot_sv_history(title="Apo 2-comp NS, subprocess path")
        """
        import os
        import matplotlib.pyplot as plt

        svs = self.sv_history
        if not svs:
            print("No SV history found (no callback.txt entries yet).")
            return
        if title is None:
            folder_name = os.path.basename(
                (self.analysis_folder or "").rstrip("/\\")
            )
            title = f"SV history — {folder_name}"
        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(svs, lw=1.5)
        ax.set_xlabel("evaluation")
        ax.set_ylabel("best SV so far")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        plt.show()

    def live_status(self):
        """Return a single dict snapshot of where this run stands right now.

        One-call replacement for the scattered probe pattern (``sv_history``
        property + ``check_progress`` + ``RunRegistry.read_manifest`` +
        ``getattr(self, 'subprocess_returncode', None)`` + ...) used in
        diagnostic notebook cells.  Pure read: scans disk, never mutates.
        Safe to invoke from ``aicKernelEval`` (issue ai-context-vscode#1)
        or any sync cell, including while the run is still in flight.

        Returns
        -------
        dict
            Keys (all best-effort; missing data → ``None``):

            - ``phase`` (str): one of ``'pending'``, ``'running'``,
              ``'completed'``, ``'failed'``, ``'unknown'``.  Derived from
              the manifest's ``status`` field plus any
              ``subprocess_returncode`` available.
            - ``n_evals`` (int): number of accepted optimizer evaluations
              recorded in ``callback.txt`` so far.
            - ``best_fv`` (float): inverted from ``best_sv`` (matches
              ``check_progress`` arithmetic).
            - ``best_sv`` (float): best score-value-so-far on the 0-100
              scale.
            - ``elapsed_s`` (float): seconds since manifest ``start_time``,
              or ``None`` if the manifest isn't available yet.
            - ``analysis_folder`` (str): from ``self.analysis_folder``.
            - ``work_folder`` (str): from ``self.work_folder``, falling back
              to walking ``analysis_folder`` for ``callback.txt``.
            - ``subprocess_pid`` (int or None): from manifest.
            - ``subprocess_returncode`` (int or None): from
              ``self.subprocess_returncode`` or manifest.
            - ``manifest`` (dict or None): the full ``RUN_MANIFEST.json``
              contents from the analysis folder, when present.

        Examples
        --------
        From a notebook cell while the run is in flight::

            run_sub.live_status()

        From outside the kernel via ai-context-vscode#1::

            aicKernelEval(expression="run_sub.live_status()")
        """
        import os
        from datetime import datetime, timezone

        analysis_folder = self.analysis_folder
        work_folder = self.work_folder

        # Try to load the per-run manifest (RunRegistry breadcrumb).
        manifest = None
        if analysis_folder:
            try:
                from molass.Rigorous.RunRegistry import read_manifest
                manifest = read_manifest(analysis_folder)
            except Exception:
                manifest = None

        # If work_folder isn't set on the RunInfo, try the manifest, then
        # fall back to a quick filesystem scan.  This is the same fallback
        # pattern that diagnostic cells (e.g. 13h cell [6d]) hand-roll.
        if work_folder is None and manifest is not None:
            work_folder = manifest.get("work_folder")
        if work_folder is None and analysis_folder and os.path.isdir(analysis_folder):
            for root, _dirs, files in os.walk(analysis_folder):
                if "callback.txt" in files:
                    work_folder = root
                    break

        # SV history (cheap; reads callback.txt files only).
        n_evals = 0
        best_sv = None
        best_fv = None
        if analysis_folder:
            try:
                from molass.Rigorous.CurrentStateUtils import parse_sv_history
                svs = parse_sv_history(analysis_folder)
                n_evals = len(svs)
                if n_evals:
                    import math
                    best_sv = float(svs[-1])
                    # Invert SV = -200/(1+exp(-1.5*fv))+100
                    try:
                        best_fv = -math.log(200.0 / (100.0 - best_sv) - 1.0) / 1.5
                    except (ValueError, ZeroDivisionError):
                        best_fv = None
            except Exception:
                pass

        # Subprocess returncode: prefer the live attribute (set by
        # RigorousImplement on process.wait()), fall back to manifest.
        rc = getattr(self, "subprocess_returncode", None)
        sub_pid = None
        if manifest is not None:
            if rc is None:
                rc = manifest.get("subprocess_returncode")
            sub_pid = manifest.get("subprocess_pid")

        # Phase: combine manifest status + returncode.
        status = (manifest or {}).get("status")
        if rc is not None and rc != 0:
            phase = "failed"
        elif rc == 0 or status == "completed":
            phase = "completed"
        elif status in ("running", "starting"):
            phase = "running"
        elif status == "pending":
            phase = "pending"
        else:
            phase = "unknown"

        # Elapsed time from manifest start_time (UTC ISO).
        elapsed_s = None
        start_time = (manifest or {}).get("start_time")
        if start_time:
            try:
                t0 = datetime.fromisoformat(start_time)
                if t0.tzinfo is None:
                    t0 = t0.replace(tzinfo=timezone.utc)
                elapsed_s = (datetime.now(timezone.utc) - t0).total_seconds()
            except (ValueError, TypeError):
                elapsed_s = None

        return {
            "phase": phase,
            "n_evals": n_evals,
            "best_fv": best_fv,
            "best_sv": best_sv,
            "elapsed_s": elapsed_s,
            "analysis_folder": analysis_folder,
            "work_folder": work_folder,
            "subprocess_pid": sub_pid,
            "subprocess_returncode": rc,
            "manifest": manifest,
        }

    @property
    def run_complete_path(self):
        """Path to run_complete.json written when the optimizer finishes normally.

        The file is always created on completion (no env-var required) at
        ``<analysis_folder>/optimized/figs/run_complete.json``.

        It is the canonical, zero-parse-required answer to
        "what was the best result?" for AI tools and notebook cells in a
        new session.

        Returns
        -------
        str
            Absolute path to the JSON file, whether or not it exists yet.
        None
            If ``analysis_folder`` was not set on this RunInfo.
        """
        import os
        if self.analysis_folder is None:
            return None
        return os.path.join(
            os.path.abspath(self.analysis_folder),
            "optimized", "figs", "run_complete.json",
        )

    def load_run_complete(self):
        """Load and return the run_complete.json written on job completion.

        Returns
        -------
        dict
            Keys: ``schema_version``, ``completed_at``, ``best_fv``,
            ``best_sv``, ``n_evals``, ``n_accepted``, ``analysis_folder``.

        Raises
        ------
        FileNotFoundError
            If the file does not exist yet (job still running, or completed
            before this fix was active).
        ValueError
            If ``analysis_folder`` is not set on this RunInfo.

        Examples
        --------
        ::

            rc = run_sub.load_run_complete()
            print(f"best_sv = {rc['best_sv']:.2f}")
        """
        import json, os
        path = self.run_complete_path
        if path is None:
            raise ValueError(
                "No analysis_folder stored in this RunInfo. "
                "Pass analysis_folder= to optimize_rigorously()."
            )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"run_complete.json not found: {path}\n"
                "The job may still be running, or it completed before "
                "this feature was active (molass-legacy fix #AI-B required)."
            )
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)