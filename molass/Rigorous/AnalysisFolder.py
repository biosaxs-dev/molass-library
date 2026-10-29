"""
    Rigorous.AnalysisFolder
    =======================

    One call to open an analysis folder (molass-library#344): ``molass.load_analysis(folder)``.
"""
import os


class AnalysisInfo:
    """Everything about a finished (or running) analysis folder, from :func:`load_analysis`.

    Attributes
    ----------
    analysis_folder : str
    result : Decomposition or None
        The rigorous-optimization result of the selected job (``result.fv``, ``result.sv``),
        ``None`` while no job has produced a result yet.
    jobid : str or None
        The job ``result`` was loaded from.
    decomp : Decomposition
        The initial (estimator) decomposition rebuilt from the recipe.
    ssd, trimmed : SecSaxsData
        The raw and the trimmed data.
    recipe : dict
        The ``recipe.json`` contents.
    jobs : list of JobInfo
        Per job: ``best_fv``, ``iterations``, ``n_nonfinite`` (rejected iterations), ...
    manifest : dict or None
        ``RUN_MANIFEST.json`` with ``status`` / ``phase`` brought up to date.
    """

    def __init__(self, analysis_folder, result, jobid, decomp, ssd, trimmed, recipe, jobs, manifest):
        self.analysis_folder = analysis_folder
        self.result = result
        self.jobid = jobid
        self.decomp = decomp
        self.ssd = ssd
        self.trimmed = trimmed
        self.recipe = recipe
        self.jobs = jobs
        self.manifest = manifest

    @property
    def best_job(self):
        """The ``JobInfo`` with the lowest objective value, or ``None``."""
        return min(self.jobs, key=lambda j: j.best_fv) if self.jobs else None

    @property
    def fv(self):
        """Objective value of the loaded result (``None`` without a result)."""
        return None if self.result is None else getattr(self.result, 'fv', None)

    @property
    def sv(self):
        """Score value (0-100) of the loaded result (``None`` without a result)."""
        return None if self.result is None else getattr(self.result, 'sv', None)

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

    def summary(self):
        """Multi-line text: result, jobs, rejected iterations, recipe."""
        r = self.recipe
        lines = [f"analysis folder: {self.analysis_folder}"]
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
        if self.result is None:
            lines.append("result: none yet (no job has a real result)")
        else:
            lines.append(f"result: job {self.jobid}, fv={self.fv:.4f}, sv={self.sv:.2f}")
        lines.append(f"jobs: {self.n_jobs}, iterations: {self.n_iterations}, "
                     f"rejected (non-finite): {self.n_nonfinite}, stalled jobs: {self.stalled_jobs}")
        for j in self.jobs:
            lines.append(f"  job {j.id}: {j.iterations} iterations, best fv={j.best_fv:.4f}, "
                         f"non-finite {j.n_nonfinite}")
        return "\n".join(lines)

    def __repr__(self):
        return f"AnalysisInfo({os.path.basename(os.path.normpath(self.analysis_folder))!r}, jobid={self.jobid!r}, fv={self.fv}, n_jobs={self.n_jobs})"

    def __str__(self):
        return self.summary()


def load_analysis(analysis_folder, jobid='best', rgcurve=None, in_folder=None):
    """Open an analysis folder: best result, its score value, jobs, rejected iterations and recipe.

    The one call for "what happened in this analysis folder", whether the run is finished or still
    going. It rebuilds the decomposition from ``recipe.json``, loads the result of the job selected
    by ``jobid`` and lists the jobs; ``print(info)`` (or ``info.summary()``) answers the usual
    questions at once.

    Parameters
    ----------
    analysis_folder : str
        Same value passed to ``optimize_rigorously(analysis_folder=...)``.
    jobid : str or None, optional
        ``'best'`` (default) loads the job with the lowest objective value, ``None`` the latest
        valid job, anything else that job id (e.g. ``'001'``).
    rgcurve : RgCurve, optional
        Passed to ``load_rigorous_result`` to avoid recomputing the Rg curve.
    in_folder : str, optional
        Folder holding the input data, for an analysis folder made on another machine (#348).

    Returns
    -------
    AnalysisInfo
        With ``result``, ``decomp``, ``ssd``, ``trimmed``, ``recipe``, ``jobs`` and ``manifest``.
        ``result`` is ``None`` while no job has a result yet.

    Examples
    --------
    ::

        import molass
        info = molass.load_analysis("analysis-001")
        print(info)                       # result, SV, jobs, rejected iterations, recipe
        info.result.plot_components()
        info.sv, info.n_nonfinite
    """
    from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe
    from molass.Rigorous.CurrentStateUtils import (
        list_rigorous_jobs, load_rigorous_result, fv_to_sv, NoCompletedJobError,
    )
    from molass.Rigorous.RunRegistry import read_manifest

    analysis_folder = os.path.abspath(analysis_folder)
    ssd, trimmed, decomp, recipe = rebuild_decomposition_from_recipe(analysis_folder, in_folder=in_folder)
    jobs = list_rigorous_jobs(analysis_folder)
    try:
        result = load_rigorous_result(decomp, analysis_folder, jobid=jobid, rgcurve=rgcurve)
    except NoCompletedJobError:
        result = None
    loaded = None
    if result is not None:
        if isinstance(jobid, str) and jobid != 'best':
            loaded = jobid
        elif jobs:
            loaded = (min(jobs, key=lambda j: j.best_fv) if jobid == 'best' else jobs[-1]).id
        job = next((j for j in jobs if j.id == loaded), None)
        if job is not None and getattr(result, 'fv', None) is None:
            result.fv = job.best_fv
            result.sv = float(fv_to_sv(job.best_fv))
    return AnalysisInfo(analysis_folder, result, loaded, decomp, ssd, trimmed, recipe, jobs,
                        read_manifest(analysis_folder, refresh=True))
