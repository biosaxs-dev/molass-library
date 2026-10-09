"""
Tests for RigorousImplement.build_pipeline_recipe() -- the single shared
builder for pipeline_recipe dicts, extracted so molass-gui's UpgradedView
(and any other external recipe builder) doesn't need its own, independently
maintained dict-literal that can silently diverge from the library's own
auto-construct path (_build_auto_recipe).

See: https://github.com/biosaxs-dev/molass-library/issues/292
"""
import json


class _DummyCurve:
    model = 'egh'


class _DummyChannel:
    def __init__(self, pickat):
        self.pickat = pickat


class _DummySsd:
    def __init__(self, uv_pickat=None, xr_pickat=None):
        self.uv = _DummyChannel(uv_pickat) if uv_pickat is not None else None
        self.xr = _DummyChannel(xr_pickat) if xr_pickat is not None else None


class _DummyDecomp:
    def __init__(self, num_components=2, model='egh', ssd=None):
        self.num_components = num_components
        self.xr_ccurves = [type('C', (), {'model': model})()]
        if ssd is not None:
            self.ssd = ssd


def test_build_pipeline_recipe_minimal_defaults():
    """With no extra args, only the core keys appear, derived from decomposition."""
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe

    recipe = build_pipeline_recipe(_DummyDecomp(num_components=3, model='sdm'))

    assert recipe == {
        "num_components": 3,
        "model": "sdm",
        "method": "bh",
        "decomp_params": {},
        "trim_params": {},
        "baseline_params": {},
    }
    json.dumps(recipe)


def test_build_pipeline_recipe_overrides_and_extras():
    """Explicit overrides win over decomposition-derived defaults; **extra
    passes through untouched -- this is what lets molass-gui's UpgradedView
    attach its own pore_dist/auto_constraint/xr_ranks fields without needing
    its own separate dict-literal."""
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe

    recipe = build_pipeline_recipe(
        _DummyDecomp(num_components=2, model='egh'),
        method='DE', model='grm', num_components=5,
        decomp_params={'proportions': [1, 2]},
        niter=7,
        pore_dist='lognormal', auto_constraint=True, xr_ranks=[1, 2, 3],
    )

    assert recipe['method'] == 'de'
    assert recipe['model'] == 'grm'
    assert recipe['num_components'] == 5
    assert recipe['decomp_params'] == {'proportions': [1, 2]}
    assert recipe['niter'] == 7
    assert recipe['pore_dist'] == 'lognormal'
    assert recipe['auto_constraint'] is True
    assert recipe['xr_ranks'] == [1, 2, 3]
    json.dumps(recipe)


def test_build_pipeline_recipe_captures_pickat_from_decomposition_ssd():
    """uv_pickat/xr_pickat are read off decomposition.ssd when ssd= isn't given."""
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe

    decomp = _DummyDecomp(ssd=_DummySsd(uv_pickat=290.0, xr_pickat=0.03))
    recipe = build_pipeline_recipe(decomp)

    assert recipe['uv_pickat'] == 290.0
    assert recipe['xr_pickat'] == 0.03


def test_build_pipeline_recipe_ssd_override_takes_precedence():
    """An explicitly-given ssd= wins over decomposition.ssd -- the case
    UpgradedView relies on (its own trimmed SSD is authoritative)."""
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe

    decomp = _DummyDecomp(ssd=_DummySsd(uv_pickat=280.0, xr_pickat=0.02))
    override_ssd = _DummySsd(uv_pickat=295.0, xr_pickat=0.025)

    recipe = build_pipeline_recipe(decomp, ssd=override_ssd)

    assert recipe['uv_pickat'] == 295.0
    assert recipe['xr_pickat'] == 0.025


def test_build_pipeline_recipe_omits_pickat_when_unavailable():
    """No ssd at all -- keys absent, not a crash or a spurious default."""
    from molass.Rigorous.RigorousImplement import build_pipeline_recipe

    recipe = build_pipeline_recipe(_DummyDecomp())

    assert 'uv_pickat' not in recipe
    assert 'xr_pickat' not in recipe


def test_build_auto_recipe_delegates_to_build_pipeline_recipe():
    """_build_auto_recipe's own output is unchanged after refactoring it to
    call build_pipeline_recipe() internally -- same dict shape as before
    #292's refactor (regression guard)."""
    from molass.Rigorous.RigorousImplement import _build_auto_recipe

    decomp = _DummyDecomp(num_components=2, model='egh',
                          ssd=_DummySsd(uv_pickat=290.0, xr_pickat=0.03))
    recipe = _build_auto_recipe(decomp, method='BH', niter=20)

    assert recipe['num_components'] == 2
    assert recipe['model'] == 'egh'
    assert recipe['method'] == 'bh'
    assert recipe['niter'] == 20
    assert recipe['uv_pickat'] == 290.0
    assert recipe['xr_pickat'] == 0.03
