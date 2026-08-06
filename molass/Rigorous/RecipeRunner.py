"""RecipeRunner — library-side recipe-based optimizer construction.

This module is the testable counterpart to molass-legacy's optimizer_recipe.py.
The subprocess calls optimizer_recipe.py which delegates here; notebooks test
this function directly, bypassing the subprocess machinery entirely.
"""


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
    import os, json
    import numpy as np

    # --- locate files ---
    optimizer_folder = os.path.dirname(os.path.dirname(work_folder))  # .../optimized

    in_folder_file = os.path.join(work_folder, 'in_folder.txt')
    if not os.path.exists(in_folder_file):
        raise FileNotFoundError(f"in_folder.txt not found in {work_folder}")
    with open(in_folder_file) as f:
        in_folder = f.read().strip()

    recipe_file = os.path.join(optimizer_folder, 'recipe.json')
    if os.path.exists(recipe_file):
        with open(recipe_file) as f:
            recipe = json.load(f)
    else:
        raise FileNotFoundError(f"recipe.json not found at {recipe_file}")

    # --- rebuild SSD pipeline ---
    from molass.DataObjects import SecSaxsData as SSD

    n_components = recipe.get('num_components', 3)
    model = recipe.get('model', 'egh').lower()
    method = recipe.get('method', 'bh').lower()
    trim_params = recipe.get('trim_params', {})
    baseline_params = recipe.get('baseline_params', {})
    decomp_params = dict(recipe.get('decomp_params', {}))
    decomp_params['num_components'] = n_components

    ssd = SSD(in_folder)
    ssd_trimmed = ssd.trimmed_copy(**trim_params)
    ssd_corrected = ssd_trimmed.corrected_copy(**baseline_params)
    decomp = ssd_corrected.quick_decomposition(**decomp_params)
    egh_decomp = decomp  # keep EGH source for LumpingConstraint boundaries
    if model != 'egh':
        decomp = decomp.upgrade(model=model)

    # Pre-cache so score() doesn't recompute Guinier per frame.
    decomp.get_rg_curve()
    score = decomp.score(trimmed_ssd=ssd_trimmed)

    # Mirror parent's LumpingConstraint auto-application for DE with 3+ components.
    # The parent applies it to its own optimizer; the subprocess must do the same.
    if method == 'de' and n_components >= 3:
        try:
            from molass.Rigorous.LumpingConstraint import LumpingConstraint
            score.optimizer._constraints = [LumpingConstraint(egh_decomp)]
        except Exception:
            pass

    return score
