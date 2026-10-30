"""
    Rigorous.AnalysisFolder
    =======================

    One call to open an analysis folder (molass-library#344): ``molass.load_analysis(folder)``.
"""
import os

from molass.Rigorous.AnalysisStatus import AnalysisStatus


class AnalysisInfo(AnalysisStatus):
    """Everything about a finished (or running) analysis folder, from :func:`load_analysis`.

    Extends :class:`~molass.Rigorous.AnalysisStatus.AnalysisStatus` (the files only: jobs, manifest, recipe,
    ``diagnose()``) with the rebuilt decomposition and the loaded result.

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
        super().__init__(analysis_folder, recipe, jobs, manifest)
        self.result = result
        self.jobid = jobid
        self.decomp = decomp
        self.ssd = ssd
        self.trimmed = trimmed

    @property
    def fv(self):
        """Objective value of the loaded result (``None`` without a result)."""
        return None if self.result is None else getattr(self.result, 'fv', None)

    @property
    def sv(self):
        """Score value (0-100) of the loaded result (``None`` without a result)."""
        return None if self.result is None else getattr(self.result, 'sv', None)

    @property
    def component_skewness(self):
        """Skewness of the elution curve of each component of the result (negative = fronting);
        ``None`` without a result, or when the result cannot tell."""
        get = getattr(self.result, 'get_skewnesses', None)
        if get is None:
            return None
        try:
            return get()
        except Exception:               # an optional line of summary(): never let it break the summary
            return None

    def _result_lines(self):
        if self.result is None:
            return ["result: none yet (no job has a real result)"]
        lines = [f"result: job {self.jobid}, fv={self.fv:.4f}, sv={self.sv:.2f}"]
        skews = self.component_skewness
        if skews is not None:
            lines.append("component skewness (negative = fronting): " + ", ".join(f"{s:.2f}" for s in skews))
        return lines

    def __repr__(self):
        return f"AnalysisInfo({os.path.basename(os.path.normpath(self.analysis_folder))!r}, jobid={self.jobid!r}, fv={self.fv}, n_jobs={self.n_jobs})"


def load_analysis(analysis_folder, jobid='best', rgcurve=None, in_folder=None, light=False):
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
    light : bool, optional
        ``True`` does not rebuild the decomposition: it returns the :class:`AnalysisStatus` of
        :func:`molass.analysis_status` (files only, seconds instead of minutes; no ``result``,
        ``decomp``, ``ssd``, ``trimmed``), and ``jobid``, ``rgcurve`` and ``in_folder`` are not used (#352).
        Default ``False``.

    Returns
    -------
    AnalysisInfo
        With ``result``, ``decomp``, ``ssd``, ``trimmed``, ``recipe``, ``jobs`` and ``manifest``.
        ``result`` is ``None`` while no job has a result yet. (:class:`AnalysisStatus` for ``light=True``.)

    Examples
    --------
    ::

        import molass
        info = molass.load_analysis("analysis-001")
        print(info)                       # result, SV, jobs, rejected iterations, recipe
        info.result.plot_components()
        info.sv, info.n_nonfinite
    """
    if light:
        from molass.Rigorous.AnalysisStatus import analysis_status
        return analysis_status(analysis_folder)
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
