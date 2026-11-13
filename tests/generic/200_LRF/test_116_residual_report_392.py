"""molass-library#392: Decomposition.get_residuals / get_residual_report (residual against the measured data)."""
import numpy as np
import pytest

from molass.LowRank.ResidualReport import durbin_watson, dw_columns


def test_durbin_watson_reference_values():
    rng = np.random.default_rng(0)
    white = rng.standard_normal(20000)
    assert durbin_watson(white) == pytest.approx(2.0, abs=0.05)
    assert durbin_watson(np.cumsum(white)) < 0.01                    # strong positive autocorrelation
    assert durbin_watson(np.array([1.0, -1.0] * 50)) == pytest.approx(4.0, abs=0.1)   # alternating
    assert durbin_watson(10 * white) == pytest.approx(durbin_watson(white))           # scale-free
    assert np.isnan(durbin_watson(np.zeros(5)))
    assert dw_columns(np.column_stack([white, np.cumsum(white)])).shape == (2,)


@pytest.fixture(scope="module")
def decompositions():
    import molass
    from molass.Testing import simulate_tiny
    molass.set_progress(False)
    corrected = simulate_tiny().trimmed_copy().corrected_copy()
    corrected.get_rg_curve()
    corrected.estimate_mapping()
    return corrected, {k: corrected.quick_decomposition(num_components=k, proportions=[1] * k) for k in (1, 2)}


def test_residual_is_that_of_the_measured_data_in_units_of_the_error(decompositions):
    corrected, decomps = decompositions
    d = decomps[2]
    Z = d.get_residuals()
    R = d.get_residuals(error_weighted=False)
    assert Z.shape == corrected.xr.M.shape
    np.testing.assert_allclose(Z * corrected.xr.E, R)
    M, C, P, _ = d.get_xr_matrices()
    denoised = (M - P @ C) / corrected.xr.E
    assert np.mean(Z ** 2) > np.mean(denoised ** 2)       # the rank-k matrix hides the misfit


def test_report_rejects_too_few_components_and_dw_is_scale_free(decompositions):
    corrected, decomps = decompositions
    r1 = decomps[1].get_residual_report(dmax=110)
    r2 = decomps[2].get_residual_report(dmax=110)
    assert r1.chi2 > 10 * r2.chi2 and r1.dw_q < 0.5 < r2.dw_q
    assert r1.delta_aic(r2) < 0 and r2.delta_aic(r1) > 0           # k = 2 preferred over k = 1
    assert r2.num_shannon == int(np.ceil(corrected.xr.qv.max() * 110 / np.pi))
    assert r2.aic_all_points > r2.aic                              # every q point counted: more "data"
    assert "DW along q" in repr(r2)

    E = corrected.xr.E
    try:
        corrected.xr.E = 2 * E
        r2x = decomps[2].get_residual_report(dmax=110)
    finally:
        corrected.xr.E = E
    assert r2x.dw_q == pytest.approx(r2.dw_q) and r2x.dw_t == pytest.approx(r2.dw_t)
    assert r2x.chi2 == pytest.approx(r2.chi2 / 4)


def test_dmax_is_estimated_from_the_component_rg_when_not_given(decompositions):
    _, decomps = decompositions
    r = decomps[2].get_residual_report()
    assert r.dmax_assumed and r.dmax == pytest.approx(3.5 * max(float(c.compute_rg()) for c in decomps[2].get_xr_components()))
    other = decomps[2].get_residual_report(dmax=r.dmax + 10)
    with pytest.raises(ValueError, match="same dmax"):
        r.delta_aic(other)
