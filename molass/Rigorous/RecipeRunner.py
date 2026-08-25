"""RecipeRunner — library-side recipe-based optimizer construction.

This module is the testable counterpart to molass-legacy's optimizer_recipe.py.
The subprocess calls optimizer_recipe.py which delegates here; notebooks test
this function directly, bypassing the subprocess machinery entirely.
"""


def rebuild_decomposition_from_recipe(analysis_folder):
    """Rebuild (ssd, trimmed, decomp, recipe) from an analysis_folder's recipe.json.

    Replays the same SSD -> trim -> correct -> quick_decomposition -> upgrade
    pipeline used when the analysis_folder was first created, using recipe.json
    plus any existing job's in_folder.txt as the source of truth. Shared by
    create_optimizer_from_recipe (subprocess path) and by session-reconstruction
    helpers (e.g. CurrentStateUtils.load_analysis_session) that need the initial
    decomposition without building a full legacy optimizer.

    Parameters
    ----------
    analysis_folder : str
        Same value passed to optimize_rigorously(analysis_folder=...).

    Returns
    -------
    ssd, trimmed, decomp, recipe
        ``decomp`` is the initial (estimator) decomposition -- not yet attached
        to any rigorous-optimization result. Use ``decomp.load_rigorous_result(
        analysis_folder)`` to attach the best on-disk result.
    """
    import os, json

    analysis_folder = os.path.abspath(analysis_folder)
    optimizer_folder = os.path.join(analysis_folder, "optimized")
    recipe_file = os.path.join(optimizer_folder, 'recipe.json')
    if not os.path.exists(recipe_file):
        raise FileNotFoundError(f"recipe.json not found at {recipe_file}")
    with open(recipe_file) as f:
        recipe = json.load(f)

    jobs_folder = os.path.join(optimizer_folder, "jobs")
    in_folder = None
    if os.path.isdir(jobs_folder):
        for jobid in sorted(os.listdir(jobs_folder)):
            candidate = os.path.join(jobs_folder, jobid, 'in_folder.txt')
            if os.path.exists(candidate):
                with open(candidate) as f:
                    in_folder = f.read().strip()
                break
    if in_folder is None:
        raise FileNotFoundError(f"No in_folder.txt found under any job in {jobs_folder}")

    from molass.DataObjects import SecSaxsData as SSD

    n_components = recipe.get('num_components', 3)
    model = recipe.get('model', 'egh').lower()
    pore_dist = recipe.get('pore_dist', None)
    ln_pore_sigma = recipe.get('ln_pore_sigma', None)
    trim_params = recipe.get('trim_params', {})
    baseline_params = recipe.get('baseline_params', {})
    decomp_params = dict(recipe.get('decomp_params', {}))
    decomp_params['num_components'] = n_components

    ssd = SSD(in_folder)
    trimmed = ssd.trimmed_copy(**trim_params)
    corrected = trimmed.corrected_copy(**baseline_params)
    decomp = corrected.quick_decomposition(**decomp_params)
    if model != 'egh':
        upgrade_kwargs = {}
        if pore_dist is not None:
            upgrade_kwargs['pore_dist'] = pore_dist
            if ln_pore_sigma is not None:
                upgrade_kwargs['model_params'] = {'ln_pore_sigma': ln_pore_sigma}
        decomp = decomp.upgrade(model=model, **upgrade_kwargs)

    return ssd, trimmed, decomp, recipe


def create_optimizer_from_recipe(work_folder, class_code):
    """Rebuild the SSD pipeline from recipe.json and return a ready optimizer.

    Parameters
    ----------
    work_folder : str
        Job folder (e.g. .../optimized/jobs/000).  Must contain in_folder.txt.
    class_code : str
        Model code (e.g. 'G0346' for EGH, 'G1200' for SDM).

    Returns
    -------
    score : Score
        Score object with .sv (initial SV), .optimizer, and .init_params.
        Pass score.optimizer to the solver for optimization.
    """
    import os

    optimizer_folder = os.path.dirname(os.path.dirname(work_folder))  # .../optimized
    analysis_folder = os.path.dirname(optimizer_folder)

    ssd_trimmed_and_decomp = rebuild_decomposition_from_recipe(analysis_folder)
    _ssd, ssd_trimmed, decomp, recipe = ssd_trimmed_and_decomp
    n_components = recipe.get('num_components', 3)
    method = recipe.get('method', 'bh').lower()
    # keep the pre-upgrade EGH source for LumpingConstraint boundaries -- same
    # fallback chain RigorousImplement.py uses (upgrade() sets _source_decomp).
    egh_decomp = getattr(decomp, '_source_decomp', getattr(decomp, '_parent', decomp))

    # Pre-cache so score() doesn't recompute Guinier per frame.
    decomp.get_rg_curve()
    score = decomp.score(trimmed_ssd=ssd_trimmed, function_code=recipe.get('function_code'))

    # Mirror the parent's freeze_components()/freeze_param_groups() calls -- without
    # this, a recipe-mode subprocess silently rebuilds a fully unfrozen optimizer even
    # when the caller asked for frozen_components=[...] (molass-library#260).
    _frozen_components = recipe.get('frozen_components')
    if _frozen_components is not None:
        score.optimizer.freeze_components(_frozen_components)
    _frozen_param_groups = recipe.get('frozen_param_groups')
    if _frozen_param_groups is not None:
        score.optimizer.freeze_param_groups(_frozen_param_groups)

    # Mirror parent's LumpingConstraint auto-application for DE with 3+ components.
    # The parent applies it to its own optimizer; the subprocess must do the same.
    if method == 'de' and n_components >= 3:
        try:
            from molass.Rigorous.LumpingConstraint import LumpingConstraint
            score.optimizer._constraints = [LumpingConstraint(egh_decomp)]
            # Mirror RigorousImplement's de_tol=0 override (issue: constraints reshape
            # the fitness landscape so scipy DE's std(energies)<=tol*mean fires too early).
            # 'de_tol' is not in OptimizerSettings.OPT_DEFAULT_SETTINGS, so it never
            # survives opt_settings.txt serialization to this subprocess — it must be
            # re-applied here directly against the live SerialSettings singleton, which
            # optimizer.solve() (called after this function returns) will read from.
            from molass_legacy._MOLASS.SerialSettings import set_setting
            set_setting('de_tol', 0)
        except Exception:
            pass

    # Mirror the parent's DE tight-population-init decision for reseeded rounds
    # (num_jobs / clear_jobs=False): job index > 0 in this analysis_folder means
    # init_params.txt (loaded by the caller after this function returns) came from
    # a previous round's best, not the plain estimator guess -- without this, DE's
    # population is built via latinhypercube regardless, so the reseed only ever
    # reaches 1 of popsize*n_params individuals (x0=). See molass-library#259.
    if method == 'de':
        try:
            job_index = int(os.path.basename(work_folder.rstrip('/\\')))
            if job_index > 0:
                score.optimizer._de_use_tight_init = True
        except (ValueError, TypeError):
            pass

    return score
