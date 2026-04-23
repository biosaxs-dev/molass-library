"""
Rigorous.RunInfo.py
"""

class RunInfo:
    def __init__(self, ssd, optimizer, dsets, init_params, monitor=None,
                 analysis_folder=None, decomposition=None):
        self.ssd = ssd
        self.optimizer = optimizer
        self.dsets = dsets
        self.init_params = init_params
        self.monitor = monitor
        self.analysis_folder = analysis_folder
        self.decomposition = decomposition

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

        Returns
        -------
        bool
            ``True`` if results appeared, ``False`` if timed out.

        Raises
        ------
        ValueError
            If no ``analysis_folder`` was stored (e.g. RunInfo was created
            without one).
        """
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
            decomp, self.analysis_folder, jobid=best.id, debug=debug
        )

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

    def check_progress(self, label=None):
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

        Examples
        --------
        ::

            _run_sub.check_progress()                    # after cell [6]
            _run_sub.check_progress(label="subprocess")  # explicit label

        See Also
        --------
        molass.Rigorous.check_progress : standalone form; also accepts a plain
            folder-path string when no ``RunInfo`` instance is at hand::

                from molass.Rigorous import check_progress
                check_progress("/path/to/analysis_folder")
        """
        from molass.Rigorous.CurrentStateUtils import check_progress as _impl
        _impl(self, label=label)

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