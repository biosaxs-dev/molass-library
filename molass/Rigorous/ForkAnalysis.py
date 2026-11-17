"""
    Rigorous.ForkAnalysis
    =====================

    ``molass.fork_analysis(source, new_folder, model=None, seed="auto")`` (molass-library#396): continue an
    existing analysis in a new folder, under another model or from a seed, in one call.

    Without it the steps were: load the finished analysis, ``upgrade()`` its best result and take
    ``get_rigorous_initparams()``, copy ``optimized/recipe.json`` of the source by hand and change
    ``analysis_folder_name``, call ``optimize_rigorously(pipeline_recipe=..., seed_params=...)``, and read the
    first ``f=`` line of ``jobs/000/callback.txt`` to see that the seed was really used.
"""
import os

import numpy as np

MODELS = ('egh', 'sdm', 'edm', 'lkm', 'grm')
UPGRADE_MODELS = ('sdm', 'edm', 'lkm', 'grm')

# what the recipe of a folder says about that folder, not about the analysis a fork continues
_OWN_KEYS = ('analysis_folder_name', 'note', 'seed_params', 'seeded_from', 'forked_from', 'niter')
# tied to the parameter layout of the elution model: re-derived for another model
_MODEL_KEYS = ('function_code', 'fronting', 'frozen_param_groups', 'pore_dist', 'ln_pore_sigma')


class ForkPlan:
    """What :func:`fork_analysis` is going to run (returned by ``fork_analysis(..., dry_run=True)``).

    Attributes
    ----------
    source_folder, new_folder : str
    source_model, model : str
        The model of the source analysis and of the fork.
    seed : str
        ``'best'``, ``'converted'``, ``'given'`` or ``'none'``.
    seed_params : numpy.ndarray or None
        The start parameter vector of job 000 (``None``: the estimate of the decomposition).
    seeded_from : str or None
        The text recorded in ``recipe.json`` (``seeded_from``).
    recipe : dict
        The ``pipeline_recipe`` of the new folder.
    decomposition : Decomposition
        The decomposition ``optimize_rigorously`` is called on.
    kwargs : dict
        The arguments of that call.
    info : AnalysisInfo
        The loaded source analysis.
    """

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def launch(self):
        """Start the run; returns its :class:`~molass.Rigorous.RunInfo.RunInfo`."""
        return self.decomposition.optimize_rigorously(**self.kwargs)

    def score(self, **kwargs):
        """The :class:`~molass.Rigorous.Score.Score` of the starting point of job 000 (the seed, or the estimate
        when there is none), on the optimizer the run will use: its ``fv`` / ``sv`` are what the first callback
        entry of job 000 records. Call it from the main thread of a GUI (see ``Decomposition.score``)."""
        from molass.Rigorous.Score import make_score_impl
        return make_score_impl(self.decomposition, trimmed_ssd=self.info.trimmed, params=self.seed_params, **kwargs)

    def __repr__(self):
        n = None if self.seed_params is None else len(self.seed_params)
        return (f"ForkPlan({os.path.basename(self.source_folder)!r} -> {os.path.basename(self.new_folder)!r}, "
                f"{self.source_model}->{self.model}, seed={self.seed!r}, n_params={n})")


def _check_folders(source_folder, new_folder):
    if not os.path.isfile(os.path.join(source_folder, "optimized", "recipe.json")):
        raise FileNotFoundError(f"{source_folder} is not an analysis folder (no optimized/recipe.json)")
    if os.path.exists(os.path.join(new_folder, "optimized")):
        raise FileExistsError(
            f"{new_folder} already holds an analysis: fork into a new folder (resume it with "
            "optimize_rigorously(clear_jobs=False) instead)")


def _resolve_seed(seed, changed, source_model, target):
    """``(kind, array or None)`` for the ``seed`` argument."""
    if seed is None or (isinstance(seed, str) and seed.lower() == 'none'):
        return 'none', None
    if isinstance(seed, str):
        key = seed.lower()
        if key == 'auto':
            return ('converted' if changed else 'best'), None
        if key == 'best':
            if changed:
                raise ValueError(
                    f"seed='best' evaluates the best parameters of the source as they are, but they belong to "
                    f"the {source_model.upper()} model and the fork is {target.upper()}: the parameter vectors "
                    "differ. Use seed='converted' (the best result converted to the new model, the default "
                    "for a model change), seed=None, or a vector made for the new model.")
            return 'best', None
        if key == 'converted':
            if not changed:
                raise ValueError("seed='converted' is for a model change; for the same model use seed='best'")
            return 'converted', None
        raise ValueError(f"seed must be 'auto', 'best', 'converted', None or a parameter vector, not {seed!r}")
    array = np.asarray(seed, dtype=float).ravel()
    return 'given', array


def fork_source(analysis_folder, decomp, trimmed, recipe, rgcurve=None, jobid='best'):
    """A fork source from what a caller already holds, without rebuilding the decomposition (#396).

    ``load_analysis`` rebuilds the pipeline from ``recipe.json``, which takes minutes. A program that has the
    initial decomposition ``decomp``, the trimmed data and the recipe (the GUI's result view) only needs to load
    the result of a job, which is fast. Pass the returned object as ``info=`` of :func:`plan_fork` /
    :func:`fork_analysis`.

    Returns
    -------
    types.SimpleNamespace
        ``analysis_folder``, ``result`` (the loaded result with its stored parameters), ``jobid``, ``decomp``,
        ``trimmed``, ``recipe``, ``fv``, ``sv`` -- what :func:`plan_fork` reads of an
        :class:`~molass.Rigorous.AnalysisFolder.AnalysisInfo`.

    Raises
    ------
    NoCompletedJobError
        The folder has no completed job yet.
    """
    from types import SimpleNamespace
    from molass.Global.Quiet import quiet_legacy
    from molass.Rigorous.CurrentStateUtils import list_rigorous_jobs, load_rigorous_result, fv_to_sv
    analysis_folder = os.path.abspath(analysis_folder)
    with quiet_legacy():
        result = load_rigorous_result(decomp, analysis_folder, jobid=jobid, rgcurve=rgcurve)
    jobs = list_rigorous_jobs(analysis_folder)
    if isinstance(jobid, str) and jobid != 'best':
        loaded = jobid
    elif jobs:
        loaded = (min(jobs, key=lambda j: j.best_fv) if jobid == 'best' else jobs[-1]).id
    else:
        loaded = None
    job = next((j for j in jobs if j.id == loaded), None)
    if job is not None and getattr(result, 'fv', None) is None:
        result.fv = job.best_fv
        result.sv = float(fv_to_sv(job.best_fv))
    return SimpleNamespace(analysis_folder=analysis_folder, result=result, jobid=loaded, decomp=decomp,
                           trimmed=trimmed, recipe=recipe, fv=getattr(result, 'fv', None),
                           sv=getattr(result, 'sv', None))


def plan_fork(source_folder, new_folder, model=None, seed='auto', jobid='best', match_curves=False,
              method=None, niter=None, note=None, in_folder=None, upgrade_kwargs=None, optimize_kwargs=None,
              info=None):
    """Prepare the fork (see :func:`fork_analysis`) without starting anything."""
    source_folder = os.path.abspath(source_folder)
    new_folder = os.path.abspath(new_folder)
    _check_folders(source_folder, new_folder)

    # the arguments are checked before the (slow) load of the source
    import json
    with open(os.path.join(source_folder, "optimized", "recipe.json")) as f:
        recipe_model = json.load(f).get('model')
    source_model = str(recipe_model or 'egh').lower()
    target = str(model).lower() if model is not None else source_model
    if target not in MODELS:
        raise ValueError(f"model must be one of {MODELS}, not {model!r}")
    changed = target != source_model
    if changed and target not in UPGRADE_MODELS:
        raise ValueError(f"a fork can change the model to {', '.join(m.upper() for m in UPGRADE_MODELS)}, not to "
                         f"{target.upper()} (it is the model of the quick decomposition)")
    if match_curves and not changed:
        raise ValueError("match_curves=True matches the curves of another model: it needs model=...")
    kind, given = _resolve_seed(seed, changed, source_model, target)

    from molass.Rigorous.CurrentStateUtils import NoCompletedJobError
    if info is None:
        from molass.Rigorous.AnalysisFolder import load_analysis
        info = load_analysis(source_folder, jobid=jobid, in_folder=in_folder)
    if info.result is None:
        raise NoCompletedJobError(f"{source_folder} has no completed job to fork from yet")

    upgrade_kwargs = dict(upgrade_kwargs or {})
    name = os.path.basename(os.path.normpath(source_folder))

    if kind == 'best':
        decomposition = info.decomp
        seed_params = getattr(info.result, '_rigorous_params', None)
        if seed_params is None:
            raise ValueError("the loaded result carries no stored parameters to seed from")
        seeded_from = f"best of {name} (job {info.jobid})"
    elif kind == 'converted':
        decomposition = info.result.upgrade(target, match_curves=match_curves, **upgrade_kwargs)
        seed_params = decomposition.get_rigorous_initparams()
        seeded_from = (f"best {source_model.upper()} of {name} (job {info.jobid}) converted to {target.upper()}"
                       + (", curves matched" if match_curves else ""))
    else:
        decomposition = info.decomp.upgrade(target, **upgrade_kwargs) if changed else info.decomp
        seed_params = given
        seeded_from = "given vector" if kind == 'given' else None

    recipe = {k: v for k, v in info.recipe.items() if k not in _OWN_KEYS}
    if changed:
        for key in _MODEL_KEYS:
            recipe.pop(key, None)
        pore_dist = upgrade_kwargs.get('pore_dist')
        if pore_dist is not None:
            recipe['pore_dist'] = pore_dist
        model_params = upgrade_kwargs.get('model_params') or {}
        if 'ln_pore_sigma' in model_params:
            recipe['ln_pore_sigma'] = model_params['ln_pore_sigma']
    recipe['model'] = target
    recipe['forked_from'] = source_folder
    method_name = (method or recipe.get('method') or 'bh')
    recipe['method'] = method_name.lower()
    n_iter = niter if niter is not None else info.recipe.get('niter', 20)
    recipe['niter'] = n_iter

    kwargs = dict(
        rgcurve=info.decomp.get_rg_curve(),
        analysis_folder=new_folder,
        method=method_name.upper(),
        niter=n_iter,
        trimmed_ssd=info.trimmed,
        pipeline_recipe=recipe,
        function_code=None if changed else recipe.get('function_code'),
        frozen_components=recipe.get('frozen_components'),
        frozen_param_groups=None if changed else recipe.get('frozen_param_groups'),
        seed_params=seed_params,
        seed_source=seeded_from,
        note=note if note is not None else
        f"forked from {name}" + (f": {source_model.upper()} -> {target.upper()}" if changed else ""),
    )
    kwargs.update(optimize_kwargs or {})
    return ForkPlan(source_folder=source_folder, new_folder=new_folder, source_model=source_model, model=target,
                    seed=kind, seed_params=None if seed_params is None else np.asarray(seed_params, dtype=float),
                    seeded_from=seeded_from, recipe=recipe, decomposition=decomposition, kwargs=kwargs, info=info)


def fork_analysis(source_folder, new_folder, model=None, seed='auto', jobid='best', match_curves=False,
                  method=None, niter=None, note=None, in_folder=None, dry_run=False, upgrade_kwargs=None,
                  info=None, **optimize_kwargs):
    """Continue an analysis in a new folder, under another model or from its best result (molass-library#396).

    Opens ``source_folder`` (:func:`molass.load_analysis`), copies its recipe into a new analysis with the
    elution model changed if asked, starts job 000 of ``new_folder`` from a seed, and records in
    ``recipe.json`` that it was forked (``forked_from``) and what the seed was (``seeded_from``,
    ``seed_params``). The first callback entry of the new job is the objective value of the seed:
    ``molass.analysis_status(new_folder).start_fv`` (``JobInfo.first_fv``).

    Parameters
    ----------
    source_folder : str
        A finished (or running) analysis folder with at least one completed job.
    new_folder : str
        The analysis folder to create. ``FileExistsError`` if it already holds an analysis.
    model : str or None, optional
        ``'sdm'``, ``'edm'``, ``'lkm'`` or ``'grm'`` to change the elution model (what ``upgrade()`` does);
        ``None`` keeps the model of the source.
    seed : {'auto', 'best', 'converted', None} or array-like, optional
        What job 000 starts from. ``'best'``: the best parameters of the source as they are (baselines, mapping
        and scales included; only for the same model, ``ValueError`` otherwise, and for a vector of the wrong
        length). ``'converted'``: the best result converted to the new model with ``upgrade()``
        (``match_curves`` applies); the default for a model change, and what the first steps of #396
        did by hand. ``None``: no seed, the estimate of the decomposition. An array-like: that vector.
        ``'auto'`` (default): ``'best'`` for the same model, ``'converted'`` for a model change.
    jobid : str, optional
        The job of the source whose result is used, ``'best'`` (default) or an id like ``'003'``.
    match_curves : bool, optional
        With a model change, fit the new components to the curves of the source result
        (``upgrade(model, match_curves=True)``, GRM and LKM).
    method, niter : optional
        Override the solver and the number of iterations of the source recipe (default: the same).
    note : str or None, optional
        Why the fork exists (``recipe.json`` ``note``); default ``"forked from <source>[: EGH -> GRM]"``.
    in_folder : str, optional
        Folder with the input data, as for ``load_analysis`` (#348).
    dry_run : bool, optional
        Return the :class:`ForkPlan` (recipe, seed, decomposition) without starting a run or making the
        folder. Default False.
    upgrade_kwargs : dict, optional
        Arguments for ``upgrade()`` (e.g. ``{'pore_dist': 'lognormal'}`` for SDM).
    info : AnalysisInfo or object from :func:`fork_source`, optional
        The already loaded source: skips the rebuild of the decomposition from ``recipe.json`` (minutes).
        ``jobid`` and ``in_folder`` are then not used.
    **optimize_kwargs
        Passed to ``optimize_rigorously`` (``async_``, ``monitor``, ``constraints``, ...), overriding what
        the fork sets.

    Returns
    -------
    RunInfo or ForkPlan
        The run of job 000 (``ForkPlan`` for ``dry_run=True``).

    Raises
    ------
    ValueError
        The seed does not fit the parameters of the new model (nothing is started), or an argument is
        inconsistent.

    Examples
    --------
    ::

        import molass
        run = molass.fork_analysis("Q4/analysis-EGH", "Q4/analysis-GRM-from-EGH", model="grm",
                                   match_curves=True, method="BH", niter=20, async_=True, monitor=False)
        molass.analysis_status("Q4/analysis-GRM-from-EGH").start_fv   # the fv of the converted start
    """
    plan = plan_fork(source_folder, new_folder, model=model, seed=seed, jobid=jobid, match_curves=match_curves,
                     method=method, niter=niter, note=note, in_folder=in_folder, upgrade_kwargs=upgrade_kwargs,
                     optimize_kwargs=optimize_kwargs, info=info)
    if dry_run:
        return plan
    return plan.launch()
