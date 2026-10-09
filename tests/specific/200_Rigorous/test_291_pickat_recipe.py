"""
Tests for recipe.json capturing uv_pickat/xr_pickat (the wavelength/q-value
SSD(...) was constructed with), so recipe-based SSD reconstruction
(RecipeRunner.rebuild_decomposition_from_recipe / create_optimizer_from_recipe,
and CurrentStateUtils.load_analysis_session) doesn't silently fall back to the
library defaults (280 nm / 0.02 A^-1) when the original session used a
non-default value.

See: https://github.com/biosaxs-dev/molass-library/issues/291
"""
import contextlib
import io
import json
import warnings


def test_build_auto_recipe_captures_pickat_from_decomposition_ssd():
    """uv_pickat/xr_pickat are read off decomposition.ssd.uv/.xr.pickat."""
    from molass.Rigorous.RigorousImplement import _build_auto_recipe

    class _DummyCurve:
        model = 'egh'

    class _DummyChannel:
        def __init__(self, pickat):
            self.pickat = pickat

    class _DummySsd:
        uv = _DummyChannel(290.0)
        xr = _DummyChannel(0.03)

    class _DummyDecomp:
        num_components = 2
        xr_ccurves = [_DummyCurve()]
        ssd = _DummySsd()

    recipe = _build_auto_recipe(_DummyDecomp(), method='BH')

    assert recipe['uv_pickat'] == 290.0
    assert recipe['xr_pickat'] == 0.03
    json.dumps(recipe)  # must stay JSON-serializable


def test_build_auto_recipe_omits_pickat_when_ssd_unavailable():
    """No decomposition.ssd (e.g. a bare/dummy decomposition) -> keys absent,
    not a crash or a spurious default value baked into the recipe."""
    from molass.Rigorous.RigorousImplement import _build_auto_recipe

    class _DummyCurve:
        model = 'egh'

    class _DummyDecomp:
        num_components = 2
        xr_ccurves = [_DummyCurve()]

    recipe = _build_auto_recipe(_DummyDecomp(), method='BH')

    assert 'uv_pickat' not in recipe
    assert 'xr_pickat' not in recipe


def test_rebuild_decomposition_from_recipe_applies_pickat(tmp_path, monkeypatch):
    """rebuild_decomposition_from_recipe() forwards recipe['uv_pickat']/
    ['xr_pickat'] to SSD(...) instead of silently using the library defaults."""
    from molass_data import SAMPLE1
    import molass.Rigorous.RecipeRunner as RecipeRunner

    captured = {}
    import molass.DataObjects as DataObjects
    real_ssd = DataObjects.SecSaxsData  # capture before patching -- avoids self-recursion

    def _fake_ssd(folder, **kwargs):
        captured['folder'] = folder
        captured['kwargs'] = kwargs
        return real_ssd(folder, **kwargs)

    # RecipeRunner does `from molass.DataObjects import SecSaxsData as SSD`
    # inside the function body, so patch the source it imports from.
    monkeypatch.setattr(DataObjects, 'SecSaxsData', _fake_ssd)

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
        "uv_pickat": 290.0,
        "xr_pickat": 0.03,
    }
    (optimizer_folder / "recipe.json").write_text(json.dumps(recipe))
    (job_folder / "in_folder.txt").write_text(str(SAMPLE1))

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd, trimmed, decomp, loaded_recipe = RecipeRunner.rebuild_decomposition_from_recipe(
            str(analysis_folder))

    assert captured['kwargs'] == {'uv_pickat': 290.0, 'xr_pickat': 0.03}
    assert ssd.uv.pickat == 290.0
    assert ssd.xr.pickat == 0.03


def test_rebuild_decomposition_from_recipe_defaults_when_pickat_absent(tmp_path):
    """Old recipe.json files (written before this field existed) still load,
    falling back to the library's own defaults -- not an error, not None."""
    from molass_data import SAMPLE1
    from molass.Rigorous.RecipeRunner import rebuild_decomposition_from_recipe

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
    }
    (optimizer_folder / "recipe.json").write_text(json.dumps(recipe))
    (job_folder / "in_folder.txt").write_text(str(SAMPLE1))

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()), \
         warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ssd, trimmed, decomp, loaded_recipe = rebuild_decomposition_from_recipe(
            str(analysis_folder))

    assert ssd.uv.pickat == 280  # library default, unchanged behavior
    assert ssd.xr.pickat == 0.02  # library default, unchanged behavior
