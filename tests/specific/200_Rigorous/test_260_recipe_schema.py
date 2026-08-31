"""
Tests for recipe.json capturing frozen_components/frozen_param_groups/niter/
function_code/seed_params, so subprocess reconstruction (RecipeRunner) and
Decomposition.load_analysis_session() don't silently diverge from what the
caller actually asked for.

See: https://github.com/biosaxs-dev/molass-library/issues/260
"""
import io
import contextlib
import json
import os
import warnings


def test_build_auto_recipe_minimal():
    """With no extra args, only the pre-existing keys plus the niter default appear."""
    from molass.Rigorous.RigorousImplement import _build_auto_recipe

    class _DummyCurve:
        model = 'egh'

    class _DummyDecomp:
        num_components = 2
        xr_ccurves = [_DummyCurve()]

    recipe = _build_auto_recipe(_DummyDecomp(), method='BH')

    assert recipe['num_components'] == 2
    assert recipe['model'] == 'egh'
    assert recipe['method'] == 'bh'
    assert recipe['niter'] == 20
    for key in ('frozen_components', 'frozen_param_groups', 'function_code', 'seed_params'):
        assert key not in recipe


def test_build_auto_recipe_full():
    """All optional parameters round-trip into the recipe dict."""
    from molass.Rigorous.RigorousImplement import _build_auto_recipe

    class _DummyCurve:
        model = 'sdm'

    class _DummyDecomp:
        num_components = 3
        xr_ccurves = [_DummyCurve()]

    recipe = _build_auto_recipe(
        _DummyDecomp(), method='DE', niter=7,
        frozen_components=[0, 2],
        frozen_param_groups=['xr_baseline', 'uv_baseline'],
        function_code='G1200',
        seed_params=[1.0, 2.0, 3.0],
    )

    assert recipe['niter'] == 7
    assert recipe['frozen_components'] == [0, 2]
    assert recipe['frozen_param_groups'] == ['xr_baseline', 'uv_baseline']
    assert recipe['function_code'] == 'G1200'
    assert recipe['seed_params'] == [1.0, 2.0, 3.0]
    # must be JSON-serializable end to end
    json.dumps(recipe)


def _make_decomp():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd = SSD(SAMPLE1)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
        decomp = corrected.quick_decomposition(num_components=2)
    return trimmed, corrected, decomp


def test_create_optimizer_from_recipe_applies_frozen_settings(tmp_path):
    """RecipeRunner.create_optimizer_from_recipe (the subprocess-mirror, tested
    directly per its own module docstring) must apply frozen_components /
    frozen_param_groups read from recipe.json -- not silently drop them."""
    from molass_data import SAMPLE1
    from molass.Rigorous.RecipeRunner import create_optimizer_from_recipe

    analysis_folder = tmp_path / "test_run"
    optimizer_folder = analysis_folder / "optimized"
    job_folder = optimizer_folder / "jobs" / "000"
    job_folder.mkdir(parents=True)

    recipe = {
        "num_components": 2,
        "model": "egh",
        "method": "bh",
        "decomp_params": {},
        "trim_params": {},
        "baseline_params": {},
        "niter": 5,
        "frozen_components": [0],
        "frozen_param_groups": ["xr_baseline"],
    }
    (optimizer_folder / "recipe.json").write_text(json.dumps(recipe))
    (job_folder / "in_folder.txt").write_text(str(SAMPLE1))

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        score = create_optimizer_from_recipe(str(job_folder), class_code='G0346')

    assert score.optimizer.frozen_components == [0]
    assert score.optimizer.frozen_param_groups == ["xr_baseline"]
