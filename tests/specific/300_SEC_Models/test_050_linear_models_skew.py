"""Skew of the linear-isotherm models, for a single component: positive, never fronting (molass-library#350).

LKM: Felinger et al. 2004 (J. Chromatogr. A 1043:149), Eq. (39) / (44), deduced positive, checked here against the
standardized third moment of ``lkm_pdf``. Linear EDM: inverse Gaussian, skew 3 sqrt(2/Pe). Linear GRM: positive,
numerically (the docstrings state the scope).
"""
import numpy as np
import pytest

from molass.SEC.Models.LkmLinear import lkm_pdf
from molass.SEC.Models.EdmLinear import edm_pdf
from molass.SEC.Models.GrmLinear import grm_pdf


def _moments(y, t):
    A = np.trapz(y, t)
    m = np.trapz(t * y, t) / A
    v = np.trapz((t - m) ** 2 * y, t) / A
    return A, m, v, np.trapz((t - m) ** 3 * y, t) / A / v ** 1.5


def felinger_skew(Nd, Nm, kprime):
    """Eq. (39) with n = N_m."""
    n = Nm
    return (3 / np.sqrt(n * Nd) * (n ** 2 * (kprime + 1) ** 3 + 2 * n * Nd * kprime ** 2 * (kprime + 1) + 2 * Nd ** 2 * kprime ** 3)
            / (n * (kprime + 1) ** 2 + 2 * Nd * kprime ** 2) ** 1.5)


@pytest.mark.parametrize("Pe, t0, k_MT, R", [(500, 2.0, 1.667, 4.0), (200, 2.0, 0.5, 4.0), (300, 3.0, 5.0, 2.5)])
def test_lkm_pdf_has_the_skew_of_felinger_eq_39(Pe, t0, k_MT, R):
    t = np.linspace(0.001, 60, 120001)
    A, m, v, skew = _moments(lkm_pdf(t, Pe=Pe, t0=t0, k_MT=k_MT, R=R), t)
    assert A == pytest.approx(1.0, rel=1e-3)
    assert m == pytest.approx(t0 * R, rel=1e-3)                       # first moment t0 (1 + k')
    assert skew == pytest.approx(felinger_skew(Pe / 2, k_MT * (R - 1) * t0, R - 1), rel=2e-3)
    assert skew > 0


def test_felinger_skew_is_positive_and_has_the_stated_limits():
    rng = np.random.default_rng(0)
    N = 100000
    Nd, Nm, kp = 10 ** rng.uniform(-1, 4, N), 10 ** rng.uniform(-2, 3, N), 10 ** rng.uniform(-3, 2, N)
    assert (felinger_skew(Nd, Nm, kp) > 0).all()
    assert felinger_skew(150.0, 3.0, 1e-9) == pytest.approx(3 / np.sqrt(150.0), rel=1e-6)           # k' -> 0
    assert felinger_skew(1e12, 5.0, 2.0) == pytest.approx(3 / np.sqrt(2 * 5.0), rel=1e-5)           # N_d -> infinity


def test_linear_edm_is_an_inverse_gaussian():
    t = np.linspace(0.01, 80, 160001)
    for Pe in (100, 300, 1000):
        _, m, v, skew = _moments(edm_pdf(t, Pe, 5.0, 3.0), t)
        assert m == pytest.approx(15.0, rel=1e-3)
        assert v == pytest.approx(2 * 25.0 * 9.0 / Pe, rel=2e-3)
        assert skew == pytest.approx(3 * np.sqrt(2 / Pe), rel=2e-3)


@pytest.mark.parametrize("Pe, k_ext, D_eff", [(400, 0.00533, 1e3), (150, 0.003, 1e3), (400, 0.02, 2e-4)])
def test_linear_grm_skew_is_positive(Pe, k_ext, D_eff):
    F = 1.5
    a_star = (3.0 - 1.0) / F
    t = np.linspace(0.01, 120, 240001)
    A, m, v, skew = _moments(grm_pdf(t, Pe, 5.0, k_ext, 0.004, D_eff, a_star, F), t)
    assert A == pytest.approx(1.0, rel=2e-3)
    assert m == pytest.approx(5.0 * 3.0, rel=2e-3)
    assert skew > 0


def test_grm_series_value_of_the_docstring():
    """The value quoted while deriving the cumulants: skew 0.3872 for the example of the grm_pdf docstring."""
    t = np.linspace(0.01, 80, 160001)
    F = 1.5
    _, _, v, skew = _moments(grm_pdf(t, 400, 5.0, 0.00533, 0.004, 1e3, 2.0 / F, F), t)
    assert skew == pytest.approx(0.3872, abs=2e-3)
    assert v == pytest.approx(7.796, rel=2e-3)
