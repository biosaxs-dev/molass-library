"""RecipeRunner — library-side recipe-based optimizer construction.

This module is the testable counterpart to molass-legacy's optimizer_recipe.py.
The subprocess calls optimizer_recipe.py which delegates here; notebooks test
this function directly, bypassing the subprocess machinery entirely.
"""


def _trim_kwargs_from_recipe(recipe):
    """Keyword arguments of ``trimmed_copy`` to rebuild the trimming a recipe was made with.

    New recipes record the angular range (``xr_qr``, point indices). Recipes written before it was
    recorded (molass-library#342) were made with the then default, the minimum of the Guinier
    range, so they are rebuilt with ``small_angle_limit='guinier'`` instead of today's default.
    """
    kwargs = dict(recipe.get('trim_params', {}))
    if 'xr_qr' not in kwargs and 'small_angle_limit' not in kwargs:
        if recipe.get('xr_qr') is not None:
            kwargs['xr_qr'] = tuple(recipe['xr_qr'])
        else:
            kwargs['small_angle_limit'] = 'guinier'
    return kwargs


def bundled_dataset_name(path):
    """Name of the ``molass_data`` sample (e.g. ``'SAMPLE1'``) that ``path`` is, or ``None``."""
    import os
    if not path:
        return None
    try:
        import molass_data
    except ImportError:
        return None
    target = os.path.normcase(os.path.abspath(path))
    for name in dir(molass_data):
        if name.startswith('SAMPLE'):
            folder = getattr(molass_data, name)
            if isinstance(folder, str) and os.path.normcase(os.path.abspath(folder)) == target:
                return name
    return None


def _bundled_dataset_folder(name):
    import os
    try:
        import molass_data
    except ImportError:
        return None
    folder = getattr(molass_data, name, None) if name else None
    return folder if isinstance(folder, str) and os.path.isdir(folder) else None


def resolve_input_folder(analysis_folder, recipe, in_folder=None):
    """Find the folder holding the input data of an analysis, in order of portability (#348).

    1. ``in_folder``, the caller's override;
    2. ``recipe['dataset']`` (a bundled ``molass_data`` sample name, recorded by new recipes);
    3. the absolute path stored in the ``in_folder.txt`` of the first job, if it still exists;
    4. fallbacks for folders made before ``dataset`` was recorded: the bundled sample named like the
       last component of the stored path (the stored path points into the ``molass_data`` of the machine
       that made the analysis), or the ``temp_in_folder`` export inside the (possibly moved)
       analysis folder.

    Raises
    ------
    FileNotFoundError
        Naming the missing path and the ``in_folder`` override.
    """
    import os

    if in_folder is not None:
        if not os.path.isdir(in_folder):
            raise FileNotFoundError(f"in_folder={in_folder!r} does not exist")
        return in_folder

    dataset_folder = _bundled_dataset_folder(recipe.get('dataset'))
    if dataset_folder is not None:
        return dataset_folder

    jobs_folder = os.path.join(analysis_folder, "optimized", "jobs")
    stored = None
    if os.path.isdir(jobs_folder):
        for jobid in sorted(os.listdir(jobs_folder)):
            candidate = os.path.join(jobs_folder, jobid, 'in_folder.txt')
            if os.path.exists(candidate):
                with open(candidate) as f:
                    stored = f.read().strip()
                break

    if stored:
        if os.path.isdir(stored):
            return stored
        leaf = os.path.basename(os.path.normpath(stored.replace('\\', '/')))
        folder = _bundled_dataset_folder(leaf)
        if folder is not None:
            return folder
        if leaf == 'temp_in_folder':
            relocated = os.path.join(analysis_folder, 'temp_in_folder')
            if os.path.isdir(relocated):
                return relocated
        raise FileNotFoundError(
            f"The input data folder recorded for {analysis_folder} does not exist here: {stored}\n"
            f"Pass in_folder=<the folder holding the data> to rebuild_decomposition_from_recipe() "
            f"(or load_analysis_session()) to use a copy at another location.")
    if recipe.get('dataset'):
        raise FileNotFoundError(
            f"The bundled dataset {recipe['dataset']!r} recorded in the recipe is not available "
            f"(is molass_data installed?). Pass in_folder=<the folder holding the data> to override.")
    raise FileNotFoundError(
        f"No in_folder.txt found under any job in {jobs_folder}. "
        f"Pass in_folder=<the folder holding the data> to override.")


def rebuild_decomposition_from_recipe(analysis_folder, in_folder=None):
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
    in_folder : str, optional
        Folder holding the input data, overriding what the analysis folder records. Use it to
        reopen an analysis on another machine or after the data moved (#348). By default the
        bundled ``molass_data`` sample named in ``recipe.json`` (``dataset``) is used, then the
        absolute path stored in the first job's ``in_folder.txt``; see :func:`resolve_input_folder`.

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

    in_folder = resolve_input_folder(analysis_folder, recipe, in_folder=in_folder)

    from molass.DataObjects import SecSaxsData as SSD

    n_components = recipe.get('num_components', 3)
    model = recipe.get('model', 'egh').lower()
    pore_dist = recipe.get('pore_dist', None)
    ln_pore_sigma = recipe.get('ln_pore_sigma', None)
    baseline_params = recipe.get('baseline_params', {})
    decomp_params = dict(recipe.get('decomp_params', {}))
    decomp_params['num_components'] = n_components
    if 'molass_version' not in recipe and 'proportions' in decomp_params:
        # Recipes written before molass_version/rg_order_weight were recorded (#299)
        # were created when the quick proportional fit had no Rg-order term (#295):
        # keep rebuilding them that way instead of with today's default.
        decomp_params.setdefault('rg_order_weight', 0)
    # uv_pickat/xr_pickat round-trip the wavelength/q-value SSD(...) was
    # originally constructed with (see _build_auto_recipe) -- omitted (None)
    # for recipe.json files written before this field existed, which falls
    # back to the library's own defaults, matching prior behavior exactly.
    ssd_kwargs = {}
    if recipe.get('uv_pickat') is not None:
        ssd_kwargs['uv_pickat'] = recipe['uv_pickat']
    if recipe.get('xr_pickat') is not None:
        ssd_kwargs['xr_pickat'] = recipe['xr_pickat']

    ssd = SSD(in_folder, **ssd_kwargs)
    # The trimming must see the anomaly_handling option the recipe was made with (it is recorded only when
    # switched off); the caller's setting is restored afterwards, this may run inside a notebook (#310).
    from molass.Global.Options import get_molass_options, set_molass_options
    saved_handling = get_molass_options('anomaly_handling')
    set_molass_options(anomaly_handling=recipe.get('anomaly_handling', saved_handling))
    try:
        trimmed = ssd.trimmed_copy(**_trim_kwargs_from_recipe(recipe))
    finally:
        set_molass_options(anomaly_handling=saved_handling)
    corrected = trimmed.corrected_copy(**baseline_params)
    decomp = corrected.quick_decomposition(**decomp_params)
    # Which components may front (molass-library#350). Recipes written before the policy was recorded have no
    # 'fronting' and are rebuilt with the bounds they ran with ('legacy': EGH tau >= 0, EDM b free).
    from molass.Rigorous.FrontingPolicy import resolve_fronting
    fronting = recipe.get('fronting')
    fronting_mode = list(fronting) if fronting is not None else 'legacy'
    if model != 'egh':
        upgrade_kwargs = {}
        if pore_dist is not None:
            upgrade_kwargs['pore_dist'] = pore_dist
            if ln_pore_sigma is not None:
                upgrade_kwargs['model_params'] = {'ln_pore_sigma': ln_pore_sigma}
        if model == 'edm':
            upgrade_kwargs['fronting'] = fronting_mode
        decomp = decomp.upgrade(model=model, **upgrade_kwargs)
    elif getattr(decomp, 'xr_ccurves', None) is not None:
        decomp.fronting_flags = resolve_fronting(decomp, fronting_mode)

    xr_ranks = recipe.get('xr_ranks')
    if xr_ranks is not None:
        decomp.update_xr_ranks(xr_ranks)

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

    # Mirror parent's LumpingConstraint auto-application (any method, 3+ components).
    # Condition + consequences come from ConstraintDefaults, the single source
    # of truth shared with RigorousImplement.py (molass-library#255) -- #253's
    # bug was exactly a safety override added to one copy of this logic and
    # not mirrored into the other.
    # recipe['auto_constraint']=False opts out (mirrors RigorousImplement.py's
    # pipeline_recipe.get('auto_constraint', True) check) -- see molass-gui's
    # low-confidence equal-split-fallback case.
    try:
        if recipe.get('auto_constraint', True):
            from molass.Rigorous.ConstraintDefaults import get_constraint_and_overrides
            _constraint_weight = recipe.get('constraint_weight')
            _auto_constraints, _overrides = get_constraint_and_overrides(
                method, n_components, egh_decomp, weight=_constraint_weight)
            if _auto_constraints is not None:
                score.optimizer._constraints = _auto_constraints
                # 'de_tol' is not in OptimizerSettings.OPT_DEFAULT_SETTINGS, so it never
                # survives opt_settings.txt serialization to this subprocess -- it must be
                # re-applied here directly against the live SerialSettings singleton, which
                # optimizer.solve() (called after this function returns) will read from.
                from molass_legacy._MOLASS.SerialSettings import set_setting
                for _k, _v in _overrides.items():
                    set_setting(_k, _v)
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
