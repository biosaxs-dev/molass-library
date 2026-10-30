"""
    Rigorous.AnalysisStatus
    =======================

    The light view of an analysis folder (molass-library#352, #353): ``molass.analysis_status(folder)``
    reads ``RUN_MANIFEST.json``, ``recipe.json`` and the ``callback.txt`` / ``bounds.txt`` files only. It does
    not rebuild the decomposition, so it returns within seconds, also while the analysis is still running
    (``molass.load_analysis`` needs minutes for that rebuild).
"""
import os


class AnalysisStatus:
    """What the files of an analysis folder say, without rebuilding the decomposition.

    Attributes
    ----------
    analysis_folder : str
    recipe : dict
        The ``recipe.json`` contents (``{}`` if there is none).
    jobs : list of JobInfo
        Per job: ``best_fv``, ``iterations``, ``n_nonfinite`` (rejected iterations), ...
    manifest : dict or None
        ``RUN_MANIFEST.json`` with ``status`` / ``phase`` brought up to date.
    """

    def __init__(self, analysis_folder, recipe, jobs, manifest):
        self.analysis_folder = analysis_folder
        self.recipe = recipe
        self.jobs = jobs
        self.manifest = manifest
        self._entries = {}

    # --- what the files say -------------------------------------------------------------------------------

    @property
    def best_job(self):
        """The ``JobInfo`` with the lowest objective value, or ``None``."""
        return min(self.jobs, key=lambda j: j.best_fv) if self.jobs else None

    @property
    def fv(self):
        """Lowest objective value over all jobs (``None`` while no job has a real result)."""
        job = self.best_job
        return None if job is None else job.best_fv

    @property
    def sv(self):
        """Score value (0-100) of :attr:`fv` (``None`` while no job has a real result)."""
        if self.fv is None:
            return None
        from molass.Rigorous.CurrentStateUtils import fv_to_sv
        return float(fv_to_sv(self.fv))

    @property
    def n_jobs(self):
        return len(self.jobs)

    @property
    def n_iterations(self):
        """Callback entries over all jobs."""
        return sum(j.n_entries for j in self.jobs)

    @property
    def n_nonfinite(self):
        """Iterations rejected as non-finite over all jobs."""
        return sum(j.n_nonfinite for j in self.jobs)

    @property
    def stalled_jobs(self):
        """Number of trailing jobs that did not improve the best objective value."""
        from molass.Rigorous.CurrentStateUtils import count_stalled_jobs
        return count_stalled_jobs(self.jobs)

    @property
    def is_active(self):
        """Whether the analysis is still running (from the manifest brought up to date)."""
        return self.manifest is not None and self.manifest.get('status') == 'running'

    @property
    def note(self):
        """The note given to ``optimize_rigorously(note=...)`` (``None`` if there is none), molass-library#357."""
        return self.recipe.get('note')

    @property
    def moved_from(self):
        """The folder name recorded at creation when it differs from the current one (renamed or moved
        analysis folder), else ``None``."""
        created = self.recipe.get('analysis_folder_name')
        current = os.path.basename(os.path.normpath(self.analysis_folder))
        return created if created is not None and created != current else None

    def _callback(self, job_id):
        """``(fvs, xs)`` of the callback.txt of a job, read once."""
        if job_id not in self._entries:
            from molass_legacy.Optimizer.StateSequence import read_callback_txt_impl
            cb = os.path.join(self.analysis_folder, 'optimized', 'jobs', job_id, 'callback.txt')
            try:
                fv_list, x_list = read_callback_txt_impl(cb)
            except (AssertionError, OSError, ValueError):
                fv_list, x_list = [], []
            self._entries[job_id] = ([row[1] for row in fv_list], x_list)
        return self._entries[job_id]

    @property
    def start_fv(self):
        """Objective value of the starting point of the analysis (the first entry of the first job),
        ``None`` if it cannot be read."""
        if not self.jobs:
            return None
        fvs, _ = self._callback(self.jobs[0].id)
        return float(fvs[0]) if fvs else None

    @property
    def best_params(self):
        """The parameter vector of the best entry (``numpy.ndarray``), ``None`` while there is no result."""
        import numpy as np
        job = self.best_job
        if job is None:
            return None
        fvs, xs = self._callback(job.id)
        finite = [(fv, k) for k, fv in enumerate(fvs) if np.isfinite(fv)]
        if not finite:
            return None
        return np.asarray(xs[min(finite)[1]], dtype=float)

    @property
    def bounds(self):
        """The bounds of the parameters (shape ``(n, 2)``) of the best job, ``None`` when the run did not
        record them (``bounds.txt`` is written for some elution models only)."""
        import numpy as np
        job = self.best_job
        if job is None:
            return None
        path = os.path.join(self.analysis_folder, 'optimized', 'jobs', job.id, 'bounds.txt')
        if not os.path.exists(path):
            return None
        try:
            bounds = np.loadtxt(path, ndmin=2)
        except ValueError:
            return None
        return bounds if bounds.ndim == 2 and bounds.shape[1] == 2 else None

    # --- diagnosis -----------------------------------------------------------------------------------------

    def diagnose(self, stalled_after=3, nonfinite_fraction=0.1, tol=1e-3):
        """Warnings about a stalled, at-start or on-bound run, found from the files only (molass-library#353).

        Parameters
        ----------
        stalled_after : int, optional
            Warn when this many trailing jobs did not improve the best objective value. Default 3.
        nonfinite_fraction : float, optional
            Warn when at least this fraction of the iterations was rejected as non-finite. Default 0.1.
        tol : float, optional
            Smaller differences of the objective value do not count as improvements. Default 1e-3.

        Returns
        -------
        list of str
            One sentence per finding, empty when nothing is wrong. (Not to be confused with
            ``RunInfo.diagnose()``, which breaks down the score of a single evaluation.)

        Notes
        -----
        The best entry of a converged basin-hopping job is typically its first step, so that alone is not
        reported. The checks: no job improved on the starting point; trailing jobs without improvement;
        a high fraction of non-finite iterations; a recipe written before the fronting policy
        (molass-library#350) for the EGH and EDM models; parameters at a bound (only for runs that recorded
        ``bounds.txt``).
        """
        import numpy as np
        findings = []
        if not self.jobs:
            return findings
        fv, start = self.fv, self.start_fv
        if start is not None and fv is not None and fv >= start - 1e-6:
            findings.append(f"no job improved on the starting point: best fv = start fv = {start:.4f}")
        if self.stalled_jobs >= stalled_after:
            findings.append(f"the last {self.stalled_jobs} of {self.n_jobs} jobs did not improve the best "
                            f"objective value (fv {fv:.4f}): converged, or stuck if the other warnings apply")
        if self.n_iterations > 0 and self.n_nonfinite / self.n_iterations >= nonfinite_fraction:
            findings.append(f"{self.n_nonfinite} of {self.n_iterations} iterations were rejected as "
                            f"non-finite ({100 * self.n_nonfinite / self.n_iterations:.0f} %)")
        if str(self.recipe.get('model', '')).lower() in ('egh', 'edm') and 'fronting' not in self.recipe:
            findings.append("the recipe has no 'fronting' key: the run started before the fronting policy "
                            "(molass-library#350) and used the former bounds (EGH tau >= 0, EDM b free)")
        bounds, params = self.bounds, self.best_params
        if bounds is not None and params is not None and len(params) == len(bounds):
            width = bounds[:, 1] - bounds[:, 0]
            movable = width > 0
            eps = 1e-6 * np.where(movable, width, 1.0)
            at_bound = movable & ((params - bounds[:, 0] <= eps) | (bounds[:, 1] - params <= eps))
            if at_bound.any():
                idx = [int(i) for i in np.flatnonzero(at_bound)]
                shown = ", ".join(map(str, idx[:8])) + (", ..." if len(idx) > 8 else "")
                findings.append(f"{len(idx)} of {len(params)} parameters of the best entry are at a bound "
                                f"(parameter indices {shown})")
        return findings

    # --- text ----------------------------------------------------------------------------------------------

    def _result_lines(self):
        """Lines about the best result; overridden by :class:`AnalysisInfo`."""
        if self.fv is None:
            return ["best: none yet (no job has a real result)"]
        return [f"best: job {self.best_job.id}, fv={self.fv:.4f}, sv={self.sv:.2f}"]

    def summary(self):
        """Multi-line text: result, jobs, rejected iterations, recipe, diagnosis."""
        r = self.recipe
        lines = [f"analysis folder: {self.analysis_folder}"]
        if self.moved_from is not None:
            lines.append(f"created as: {self.moved_from} (the folder was renamed or moved)")
        if self.note is not None:
            lines.append(f"note: {self.note}")
        if self.manifest is not None:
            lines.append(f"status: {self.manifest.get('status')} ({self.manifest.get('phase')})")
        lines.append(f"recipe: model={r.get('model')}, num_components={r.get('num_components')}, "
                     f"method={r.get('method')}, xr_ranks={r.get('xr_ranks')}, "
                     f"dataset={r.get('dataset')}, molass_version={r.get('molass_version')}")
        if str(r.get('model', '')).lower() in ('egh', 'edm'):
            from molass.Rigorous.FrontingPolicy import describe
            fronting = r.get('fronting')
            lines.append("fronting allowed for: " + (describe(fronting) if fronting is not None
                                                     else "(recipe written before the policy: the former bounds)"))
        lines.extend(self._result_lines())
        lines.append(f"jobs: {self.n_jobs}, iterations: {self.n_iterations}, "
                     f"rejected (non-finite): {self.n_nonfinite}, stalled jobs: {self.stalled_jobs}")
        for j in self.jobs:
            lines.append(f"  job {j.id}: {j.iterations} iterations, best fv={j.best_fv:.4f}, "
                         f"non-finite {j.n_nonfinite}")
        for finding in self.diagnose():
            lines.append(f"warning: {finding}")
        return "\n".join(lines)

    def __repr__(self):
        name = os.path.basename(os.path.normpath(self.analysis_folder))
        return f"AnalysisStatus({name!r}, fv={self.fv}, n_jobs={self.n_jobs}, active={self.is_active})"

    def __str__(self):
        return self.summary()


def analysis_status(analysis_folder):
    """The light status of an analysis folder, without rebuilding the decomposition (molass-library#352).

    Reads ``RUN_MANIFEST.json``, ``recipe.json`` and the ``callback.txt`` files of the jobs, so it returns in
    seconds also for a folder that is still being written; :func:`molass.load_analysis` rebuilds the
    decomposition from the recipe first and takes minutes. Use it to poll a running analysis, to survey many
    folders in a loop, and for :meth:`AnalysisStatus.diagnose`.

    Parameters
    ----------
    analysis_folder : str
        Same value passed to ``optimize_rigorously(analysis_folder=...)``.

    Returns
    -------
    AnalysisStatus
        With ``fv``, ``sv``, ``jobs``, ``n_nonfinite``, ``stalled_jobs``, ``is_active``, ``recipe``,
        ``manifest``, ``best_params`` and ``diagnose()``. ``print(status)`` summarizes it.

    Examples
    --------
    ::

        import molass
        status = molass.analysis_status("analysis-001")
        print(status)                 # status, recipe, best fv, jobs, warnings
        status.is_active, status.fv, status.diagnose()
    """
    import json
    from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs
    from molass.Rigorous.RunRegistry import read_manifest

    analysis_folder = os.path.abspath(analysis_folder)
    if not os.path.isdir(analysis_folder):
        raise FileNotFoundError(f"analysis folder not found: {analysis_folder}")
    try:
        with open(os.path.join(analysis_folder, 'optimized', 'recipe.json')) as f:
            recipe = json.load(f)
    except (OSError, ValueError):
        recipe = {}
    return AnalysisStatus(analysis_folder, recipe, list_rigorous_jobs(analysis_folder),
                          read_manifest(analysis_folder, refresh=True))
