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
                 analysis_folder=None, decomposition=None):
        self.ssd = ssd
        self.optimizer = optimizer
        self.dsets = dsets
        self.init_params = init_params
        self.monitor = monitor
        self.analysis_folder = analysis_folder
        self.decomposition = decomposition
        # Set by RigorousImplement for in_process=True runs:
        self.work_folder = None
        self.in_process_result = None

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