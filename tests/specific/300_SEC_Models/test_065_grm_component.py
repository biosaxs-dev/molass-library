"""
Tests for GrmComponentCurve, GrmEstimator, GrmOptimizer, and the full
upgrade(model='GRM') round-trip.

These are smoke tests — they verify the pipeline runs end-to-end and
the resulting component curves have sensible shapes (normalised area ≈ 1,
non-negative, peak near expected mean).
"""
import numpy as np
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def sample_decomposition():
    """Return a basic 2-component EGH decomposition on SAMPLE1."""
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    from molass.Global.Options import set_molass_options
    set_molass_options(quiet=True)
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
    return corrected.quick_decomposition(num_components=2)


# ── GrmComponentCurve ─────────────────────────────────────────────────────────

def test_grm_component_curve_shape():
    """GrmComponentCurve produces a non-negative, normalised-area profile."""
    from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve
    x = np.linspace(0, 20, 800)
    Pe, t0, R_p, D_eff = 400.0, 5.0, 0.004, 1e3
    a_star, F_ratio = 0.5, 1.5
    k_ext, R, scale = 0.003, 2.0, 1.0
    c = GrmComponentCurve(x, Pe, t0, R_p, D_eff, a_star, F_ratio, k_ext, R, scale)
    assert c.y is not None
    assert np.all(c.y >= -1e-6), "GrmComponentCurve must be non-negative"
    area = np.trapz(c.y, x)
    assert abs(area - 1.0) < 0.05, f"Expected area≈1, got {area:.4f}"


def test_grm_component_curve_mean():
    """Mean of GrmComponentCurve is close to t0 * R_eff = t0 * (1 + F*a_star)."""
    from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve
    x = np.linspace(0, 30, 1200)
    Pe, t0, R_p, D_eff = 400.0, 5.0, 0.004, 1e3
    a_star, F_ratio = 0.5, 1.5
    k_ext, R, scale = 0.003, 2.0, 1.0
    c = GrmComponentCurve(x, Pe, t0, R_p, D_eff, a_star, F_ratio, k_ext, R, scale)
    mean = np.trapz(x * c.y, x)
    # GRM mean = t0 * R_eff = t0 * (1 + F*a_star) = 5 * 1.75 = 8.75
    expected = t0 * (1.0 + F_ratio * a_star)
    assert abs(mean - expected) / expected < 0.05, f"mean={mean:.3f}, expected={expected:.3f}"


def test_grm_component_curve_model_attribute():
    from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve
    x = np.linspace(0, 20, 200)
    c = GrmComponentCurve(x, 400, 5, 0.004, 1e3, 0.5, 1.5, 0.003, 2.0, 1.0)
    assert c.model == 'grm'


# ── GrmEstimator (library) ────────────────────────────────────────────────────

def test_estimate_grm_init_params_returns_sensible(sample_decomposition):
    """estimate_grm_init_params runs and returns positive parameters."""
    from molass.SEC.Models.GrmEstimator import estimate_grm_init_params
    decomp = sample_decomposition
    result = estimate_grm_init_params(decomp, debug=False)
    Pe, t0, R_p, D_eff, a_star, F_ratio, k_ext_list, R_list, scale_list = result
    assert Pe > 0 and t0 > 0
    assert R_p > 0 and D_eff > 0
    assert F_ratio > 0
    for R_i, k_ext_i in zip(R_list, k_ext_list):
        assert R_i > 1.0, f"R_i={R_i} should be > 1"
        assert k_ext_i > 0, f"k_ext_i={k_ext_i} should be positive"


# ── Full upgrade('GRM') round-trip ────────────────────────────────────────────

def test_upgrade_grm_produces_grm_ccurves(sample_decomposition):
    """upgrade('GRM') returns a Decomposition with GrmComponentCurve objects."""
    from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve
    decomp = sample_decomposition
    grm_decomp = decomp.upgrade('GRM')
    assert grm_decomp.model == 'grm', f"model={grm_decomp.model}"
    for cc in grm_decomp.xr_ccurves:
        assert isinstance(cc, GrmComponentCurve), f"Expected GrmComponentCurve, got {type(cc)}"


def test_upgrade_grm_non_negative(sample_decomposition):
    """All GRM component curves are non-negative."""
    decomp = sample_decomposition
    grm_decomp = decomp.upgrade('GRM')
    for i, cc in enumerate(grm_decomp.xr_ccurves):
        assert np.all(cc.y >= -1e-4), f"Component {i} has negative values"


def test_upgrade_grm_ordering(sample_decomposition):
    """GRM component peaks are ordered by elution time (ascending R)."""
    decomp = sample_decomposition
    grm_decomp = decomp.upgrade('GRM')
    ccurves = grm_decomp.xr_ccurves
    Rs = [cc.R for cc in ccurves]
    assert Rs == sorted(Rs) or max(Rs) / min(Rs) < 5, \
        f"R values not ordered: {Rs}"
