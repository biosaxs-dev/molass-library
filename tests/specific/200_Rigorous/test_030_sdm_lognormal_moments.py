"""
Test sdm_lognormal_model_moments and refine_lognormal_params_by_moments.

See: https://github.com/biosaxs-dev/molass-library/issues/113
"""
import numpy as np
import pytest


def test_sdm_lognormal_model_moments_basic():
    """Smoke test: function returns finite (M1, Var)."""
    from molass.SEC.Models.LognormalPore import sdm_lognormal_model_moments
    M1, Var = sdm_lognormal_model_moments(
        rg=33.4, N=1716, T=3.88, N0=50000, t0=-1007,
        k=0.5, mu=4.0, sigma=0.05)
    assert np.isfinite(M1)
    assert np.isfinite(Var)
    assert Var > 0


def test_sdm_lognormal_model_moments_excluded_pore():
    """When max_rg <= rg, all pores excluded → mobile-phase only."""
    from molass.SEC.Models.LognormalPore import sdm_lognormal_model_moments
    # mu=2 → median pore ~7Å, much smaller than rg=100Å
    M1, Var = sdm_lognormal_model_moments(
        rg=100.0, N=1000, T=1.0, N0=10000, t0=500,
        k=2.0, mu=2.0, sigma=0.1)
    assert M1 == 500.0
    assert Var == pytest.approx(500.0**2 / 10000)


def test_sdm_lognormal_model_moments_matches_full_pdf():
    """Analytical moments should match empirical moments of the full PDF."""
    from molass.SEC.Models.LognormalPore import (
        sdm_lognormal_model_moments,
        sdm_lognormal_pore_gamma_pdf_fast,
    )
    # Realistic SDM lognormal params (peak inside [0, 4000])
    params = dict(N=1500, T=0.5, N0=30000, t0=200, k=2.0, mu=4.5, sigma=0.3)
    rg = 30.0

    M1_an, Var_an = sdm_lognormal_model_moments(rg=rg, **params)

    # Compute empirical moments from the full PDF
    x = np.arange(0, 4000, dtype=float)
    y = sdm_lognormal_pore_gamma_pdf_fast(
        x, 1.0, params['N'], params['T'], params['k'],
        1.5, 1.5, params['mu'], params['sigma'], rg,
        params['N0'], params['t0'])
    W = y.sum()
    M1_emp = (x * y).sum() / W
    Var_emp = (y * (x - M1_emp)**2).sum() / W

    # M1 should agree to ~1e-6 (analytical vs FFT discretization)
    assert M1_an == pytest.approx(M1_emp, rel=1e-4)
    # Variance to ~3% (FFT bin discretization broadens slightly)
    assert Var_an == pytest.approx(Var_emp, rel=0.05)


def test_refine_lognormal_params_by_moments_signature():
    """Smoke test: refinement function callable and returns 4-tuple."""
    from molass.SEC.Models.SdmEstimator import refine_lognormal_params_by_moments

    # Minimal fake decomposition with one component
    class _FakeCurve:
        def __init__(self, x, y):
            self._x, self._y = x, y
        def get_xy(self):
            return self._x, self._y

    class _FakeDecomp:
        def __init__(self, rgs, ccurves):
            self._rgs = list(rgs)
            self.xr_ccurves = ccurves
        def get_rgs(self):
            return self._rgs

    # Build a Gaussian-like component
    x = np.arange(0, 1000, dtype=float)
    y = np.exp(-((x - 500)**2) / (2 * 50**2))
    decomp = _FakeDecomp([30.0], [_FakeCurve(x, y)])

    t0_r, k_r, mu_r, sigma_r = refine_lognormal_params_by_moments(
        decomp, N=1500, T=2.5, N0=30000, t0=-500,
        k=2.0, mu=4.5, sigma=0.3)
    assert all(np.isfinite([t0_r, k_r, mu_r, sigma_r]))
    assert 0.05 <= sigma_r <= 1.5
