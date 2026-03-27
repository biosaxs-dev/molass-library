"""
Rigorous.RunInfo.py
"""

class RunInfo:
    def __init__(self, ssd, optimizer, dsets, init_params, monitor=None):
        self.ssd = ssd
        self.optimizer = optimizer
        self.dsets = dsets
        self.init_params = init_params
        self.monitor = monitor

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