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


def qamar_table1_dirichlet(Pe, t0, k_ext, R_p, D_eff, a_star, F, L=1.7):
    """Mean, variance (without the t_inj^2/12 of a rectangular pulse) and third central moment of the GRM,
    Qamar et al. 2014 (Chem. Eng. Sci. 107:192), Table 1, Dirichlet BCs. L only fixes the units (u = L/t0)."""
    u = L / t0
    D_L = u * L / Pe
    A = 2 * R_p * a_star ** 2 / (3 * k_ext) + 2 * R_p ** 2 * a_star ** 2 / (15 * D_eff)
    m1 = (L / u) * (1 + a_star * F)
    m2 = L * F / u * A + 2 * L * D_L / u ** 3 * (1 + a_star * F) ** 2
    m3 = (6 * L * D_L * (1 + a_star * F) * F / u ** 3 * A
          + L * F * a_star ** 3 / u * (4 * R_p ** 4 / (105 * D_eff ** 2) + 4 * R_p ** 3 / (15 * k_ext * D_eff) + 2 * R_p ** 2 / (3 * k_ext ** 2))
          + 12 * L * D_L ** 2 * (1 + a_star * F) ** 3 / u ** 5)
    return m1, m2, m3


@pytest.mark.parametrize("Pe, k_ext, D_eff", [(400, 0.00533, 1e3), (150, 0.003, 1e3), (400, 0.02, 2e-4)])
def test_grm_pdf_has_the_moments_of_qamar_table_1(Pe, k_ext, D_eff):
    F = 1.5
    a_star = 2.0 / F
    t = np.linspace(0.01, 120, 240001)
    _, m, v, skew = _moments(grm_pdf(t, Pe, 5.0, k_ext, 0.004, D_eff, a_star, F), t)
    m1, m2, m3 = qamar_table1_dirichlet(Pe, 5.0, k_ext, 0.004, D_eff, a_star, F)
    assert m == pytest.approx(m1, rel=2e-3)
    assert v == pytest.approx(m2, rel=3e-3)
    # the third moment weights the far tail, where the FFT inversion has a little noise: 1 % (the exact
    # agreement of the transfer function with Table 1 is to rounding error, see the cumulant check in experiment 54)
    assert skew == pytest.approx(m3 / m2 ** 1.5, rel=1e-2)
    assert m3 > 0


def test_general_sojourn_time_law_gives_a_positive_skew_and_felinger_eq_44():
    """Felinger Eq. (32) with any positive sojourn-time law: kappa2 = Y2 + Y1^2/Nd,
    kappa3 = Y3 + 3 Y1 Y2/Nd + 3 Y1^3/Nd^2, Y1 = n E[tau] + t0, Y_k = n E[tau^k]."""
    rng = np.random.default_rng(0)
    for _ in range(1000):
        n, t0, Nd = 10 ** rng.uniform(-1, 2), 10 ** rng.uniform(-1, 2), 10 ** rng.uniform(0, 4)
        m1, m2, m3 = 10 ** rng.uniform(-2, 1, 3)               # any positive moments (not necessarily consistent)
        Y1, Y2, Y3 = n * m1 + t0, n * m2, n * m3
        assert Y3 + 3 * Y1 * Y2 / Nd + 3 * Y1 ** 3 / Nd ** 2 > 0
    n, t0, Nd, ts = 7.3, 2.1, 40.0, 0.9                          # exponential sojourn times: m_k = k! ts^k
    Y1, Y2, Y3 = n * ts + t0, 2 * n * ts ** 2, 6 * n * ts ** 3
    S = (Y3 + 3 * Y1 * Y2 / Nd + 3 * Y1 ** 3 / Nd ** 2) / (Y2 + Y1 ** 2 / Nd) ** 1.5
    assert S == pytest.approx(felinger_skew(Nd, n, n * ts / t0), rel=1e-12)     # k' = n ts / t0, N_m = n


@pytest.mark.parametrize("n, ts, t0, Nd", [(20, 0.5, 10.0, 150.0), (20, 0.5, 10.0, 14400.0), (4, 2.0, 10.0, 150.0), (60, 0.2, 10.0, 40.0)])
def test_molass_sdm_has_the_second_order_skew_not_the_lkm_one(n, ts, t0, Nd):
    """sdm_monopore_pdf uses exp(Z + Z^2/(2 N0)): kappa3 = Y3 + 3 Y1 Y2/N0 (positive), equal to the LKM's skew
    only when N0 is large."""
    from molass.SEC.Models.SdmMonoPore import sdm_monopore_pdf
    t = np.linspace(0.001, 150, 150001)
    tR = t0 + n * ts
    _, m, v, skew = _moments(sdm_monopore_pdf(t, n, ts, Nd, t0, timescale=80 / tR), t)
    Y1, Y2, Y3 = n * ts + t0, 2 * n * ts ** 2, 6 * n * ts ** 3
    assert m == pytest.approx(tR, rel=1e-3)
    assert v == pytest.approx(Y2 + Y1 ** 2 / Nd, rel=2e-3)
    assert skew == pytest.approx((Y3 + 3 * Y1 * Y2 / Nd) / (Y2 + Y1 ** 2 / Nd) ** 1.5, rel=5e-3)
    assert skew > 0
    exact = felinger_skew(Nd, n, n * ts / t0)
    assert skew <= exact * (1 + 5e-3)                            # never above the LKM's skew


def test_molass_sdm_without_adsorption_is_a_gaussian():
    from molass.SEC.Models.SdmMonoPore import sdm_monopore_pdf
    t = np.linspace(0.001, 150, 150001)
    _, m, v, skew = _moments(sdm_monopore_pdf(t, 1e-9, 0.5, 150.0, 10.0, timescale=8.0), t)
    assert abs(skew) < 1e-3                                       # the LKM / linear EDM would give 3/sqrt(150) = 0.245


def _sepsey_a(eta, rho, sigma):
    """Sepsey, Bacskay and Felinger 2014 (J. Chromatogr. A 1331:52), Eq. (25), integer eta >= 0;
    rho = r_G / r_{p,0}."""
    from math import comb
    from scipy import special
    return 0.5 * sum((-rho) ** k * np.exp(k ** 2 * sigma ** 2 / 2) * comb(eta, k)
                     * special.erfc((k * sigma ** 2 + np.log(rho)) / (np.sqrt(2) * sigma)) for k in range(eta + 1))


def _lognormal_pore_cumulant(k, N, T, me, mp, mu, sigma, Rg):
    """k-th cumulant of the CF of gec_lognormal_pore_cf (no dispersion): the integrand of
    gec_lognormal_pore_integrand_impl differentiated k times at w = 0, over (Rg, infinity)."""
    from math import factorial
    from scipy import integrate
    from molass.SEC.Models.LognormalPore import distribution_func, Ksec
    f = lambda r: distribution_func(r, mu, sigma) * N * Ksec(Rg, r, me) * factorial(k) * (T * Ksec(Rg, r, mp)) ** k
    return integrate.quad(f, Rg, np.inf, limit=400)[0]


@pytest.mark.parametrize("me, mp", [(2, 1), (4, -1), (3, 0)])
@pytest.mark.parametrize("sigma", [0.3, 0.5, 1.0])
def test_lognormal_pore_cumulants_are_sepsey_eq_22_to_25(me, mp, sigma):
    """mu1 = n T a, mu2' = 2 n T^2 a, mu3' = 6 n T^3 a with a = K_SEC(eta), eta = m_e + k m_p (Eq. 22-25)."""
    from math import factorial
    N, T, r0 = 2000.0, 1.0, 12.434                             # n_perm, tau_perm, r_{p,0} of the paper's Sec. 3
    Rg = 0.4 * r0
    for k in (1, 2, 3):
        got = _lognormal_pore_cumulant(k, N, T, me, mp, np.log(r0), sigma, Rg)
        want = N * T ** k * factorial(k) * _sepsey_a(me + k * mp, Rg / r0, sigma)
        assert got == pytest.approx(want, rel=1e-6)
        assert got > 0


def test_lognormal_pore_cumulants_are_positive_also_for_non_integer_exponents():
    """Positive integrand: every cumulant is positive wherever the integral converges (eta > -1)."""
    r0 = 12.434
    for me, mp in ((1.7, 0.3), (2.5, -0.4), (1.1, -0.1)):
        for sigma in (0.3, 1.0):
            for k in (1, 2, 3):
                assert _lognormal_pore_cumulant(k, 2000.0, 1.0, me, mp, np.log(r0), sigma, 0.4 * r0) > 0


def test_qamar_table_1_third_moment_is_positive_and_gives_the_edm_limit():
    rng = np.random.default_rng(0)
    N = 100000
    p = (10 ** rng.uniform(1, 4, N), 10 ** rng.uniform(-1, 2, N), 10 ** rng.uniform(-5, 1, N), 10 ** rng.uniform(-4, -1, N),
         10 ** rng.uniform(-8, 3, N), 10 ** rng.uniform(-3, 2, N), 10 ** rng.uniform(-1, 1, N))
    _, m2, m3 = qamar_table1_dirichlet(*p)
    assert (m3 > 0).all() and (m2 > 0).all()
    _, m2, m3 = qamar_table1_dirichlet(300.0, 5.0, 1e12, 0.004, 1e12, 2.0 / 1.5, 1.5)           # k_ext, D_eff -> infinity
    assert m3 / m2 ** 1.5 == pytest.approx(3 * np.sqrt(2 / 300.0), rel=1e-6)


def test_grm_series_value_of_the_docstring():
    """The value quoted while deriving the cumulants: skew 0.3872 for the example of the grm_pdf docstring."""
    t = np.linspace(0.01, 80, 160001)
    F = 1.5
    _, _, v, skew = _moments(grm_pdf(t, 400, 5.0, 0.00533, 0.004, 1e3, 2.0 / F, F), t)
    assert skew == pytest.approx(0.3872, abs=2e-3)
    assert v == pytest.approx(7.796, rel=2e-3)
