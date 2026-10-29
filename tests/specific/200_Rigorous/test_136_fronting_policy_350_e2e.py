"""Fronting policy end to end (molass-library#350): real SAMPLE3 / SAMPLE1 fits, no optimization run.

SAMPLE3 is the bundled sample with a fronting peak (EGH tau = -7.55); SAMPLE1's components do not front.
"""
import json
import os

import numpy as np
import pytest

molass_data = pytest.importorskip("molass_data")


def _quick(sample, **kwargs):
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(getattr(molass_data, sample))
    trimmed = ssd.trimmed_copy()
    return trimmed, trimmed.corrected_copy().quick_decomposition(**kwargs)


@pytest.fixture(scope="module")
def sample3():
    return _quick("SAMPLE3", num_components=1)


def test_egh_rigorous_bounds_contain_the_fronting_start(sample3):
    """Before #350 the start (tau = -7.55) lay outside the bounds (tau >= 0): the optimizer then only found
    worse points at tau = 0 and the reported best was the start itself."""
    trimmed, decomp = sample3
    assert decomp.fronting_flags is None                      # nothing recorded yet: 'auto'
    score = decomp.score(trimmed_ssd=trimmed)
    tau_lo, tau_hi = score.optimizer.real_bounds[3]
    assert tau_lo < -7.55 < 0 < tau_hi
    assert tau_lo <= score.init_params[3] <= tau_hi

    decomp.fronting_flags = [False]                           # the former behavior
    legacy = decomp.score(trimmed_ssd=trimmed).optimizer.real_bounds[3]
    assert legacy[0] == 0
    decomp.fronting_flags = None


def test_recipe_records_the_policy_and_rebuild_follows_it(sample3, tmp_path):
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe
    from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe

    trimmed, decomp = sample3
    recipe = build_pipeline_recipe(decomp, method='BH', niter=2, ssd=trimmed)
    assert recipe['fronting'] == [True]
    json.dumps(recipe)

    def make_folder(name, rec):
        folder = tmp_path / name
        job = folder / "optimized" / "jobs" / "000"
        job.mkdir(parents=True)
        (job / "in_folder.txt").write_text(molass_data.SAMPLE3)
        (folder / "optimized" / "recipe.json").write_text(json.dumps(rec))
        return str(folder)

    new = dict(recipe)
    rebuilt = rebuild_decomposition_from_recipe(make_folder("new", new))[2]
    assert rebuilt.fronting_flags == [True]

    old = {k: v for k, v in recipe.items() if k != 'fronting'}     # a recipe written before the policy
    rebuilt_old = rebuild_decomposition_from_recipe(make_folder("old", old))[2]
    assert rebuilt_old.fronting_flags == [False]                    # resumes with the bounds it ran with


def test_optimize_rigorously_option_is_accepted_and_documented():
    import inspect
    from molass.LowRank.Decomposition import Decomposition
    sig = inspect.signature(Decomposition.optimize_rigorously)
    assert sig.parameters['fronting'].default is None
    assert 'fronting' in Decomposition.optimize_rigorously.__doc__


def test_edm_quick_stage_b_follows_the_policy():
    """SAMPLE1, three tailing/symmetric components: b >= 0 everywhere with the default; 'allow' is the former
    behavior (free b, SAMPLE1 gave b = -9.6 for component 1)."""
    trimmed, decomp = _quick("SAMPLE1")
    auto = decomp.upgrade(model='EDM', suppress_positive_b_warning=True)
    assert auto.fronting_flags == [False, False, False]
    b = [float(cc.get_params()[3]) for cc in auto.xr_ccurves]
    assert min(b) >= -1e-9, b

    # the policy is carried to the rigorous stage through the decomposition
    score = auto.score(trimmed_ssd=trimmed)
    xr_b_bounds = np.asarray(score.optimizer.real_bounds)[:9].reshape(3, 3, 2)[:, 1, :]
    assert (xr_b_bounds[:, 0] == 0).all()
    assert (np.asarray(score.init_params)[:9].reshape(3, 3)[:, 1] >= xr_b_bounds[:, 0]).all()
