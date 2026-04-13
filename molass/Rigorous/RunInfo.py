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