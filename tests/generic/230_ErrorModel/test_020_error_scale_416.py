"""molass-library#416: XrData.error_scale (model-free noise scale per q region) and Decomposition.get_curve_fit_report
(do the component curves describe the data?). Simulated frames with a known noise factor; no local data needed."""
import types
import warnings

import numpy as np
import pytest

from molass.DataObjects.XrData import XrData
from molass.LowRank.ErrorScale import compute_curve_fit_report, compute_error_scale


def _frames(noise_factor, seed=0, nq=300, nf=160):
    """Rank-1 frames: a smooth skewed (exponentially modified Gaussian) elution peak times a Guinier-like profile; the stated
    error is about 1/250 of the peak intensity at low q (SAMPLE3-like), the noise is ``noise_factor`` times the stated error."""
    from scipy.special import erfc
    rng = np.random.default_rng(seed)
    q = np.linspace(0.01, 0.3, nq)
    j = np.arange(nf, dtype=float)
    s, tau = 8.0, 14.0
    c = np.exp(-(j - 60) / tau + s ** 2 / (2 * tau ** 2)) * erfc((s ** 2 - tau * (j - 60)) / (np.sqrt(2) * s * tau))
    c = c / c.max()
    a = 1.0 * np.exp(-(q * 30.0) ** 2 / 3) + 0.01
    E = np.repeat((0.004 * (1 + 0.5 * np.exp(-q / 0.03)))[:, None], nf, axis=1)
    M = a[:, None] * c[None, :] + noise_factor * E * rng.standard_normal((nq, nf))
    return q, j, M, E, c


@pytest.mark.fast
@pytest.mark.parametrize("factor", [0.5, 1.0, 2.5])
def test_error_scale_recovers_a_known_noise_factor(factor):
    q, j, M, E, c = _frames(factor)
    xr = XrData(M, q, j, E=E)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rep = xr.error_scale()
    finite = rep.s_noise[np.isfinite(rep.s_noise)]
    assert len(finite) >= 4
    assert np.all(np.abs(finite / factor - 1) < 0.06), rep


@pytest.mark.fast
def test_error_scale_warns_only_when_the_scale_is_off():
    q, j, M, E, c = _frames(1.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        XrData(M, q, j, E=E).error_scale()               # right scale: no warning (an exception here otherwise)
    q, j, M, E, c = _frames(2.5)
    with pytest.warns(UserWarning, match="stated error"):
        rep = XrData(M, q, j, E=E).error_scale()
    assert rep.outside()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        XrData(M, q, j, E=E).error_scale(warn=False)


@pytest.mark.fast
def test_a_wrong_curve_is_not_an_error_scale_problem():
    """The stated error is right (factor 1) but the model curve is a symmetric Gaussian: the fit s is far above 1, the
    model-free noise scale stays at 1, and a free SVD fit is at the noise level."""
    q, j, M, E, c = _frames(1.0)
    xr = XrData(M, q, j, E=E)
    peak = int(np.argmax(c))
    wrong = np.exp(-0.5 * ((j - (peak + 8)) / 14.0) ** 2)
    right = c

    def decomp(curve):
        cc = types.SimpleNamespace(get_xy=lambda: (j, curve))
        return types.SimpleNamespace(xr=xr, xr_ccurves=[cc])

    bad = compute_curve_fit_report(decomp(wrong))
    good = compute_curve_fit_report(decomp(right))
    sel = np.isfinite(bad.ratio)
    strong = slice(0, 3)                                   # q < 0.1: the signal is large compared with the noise, a wrong curve shows
    assert np.all(bad.s_curves[strong] > 3) and np.all(bad.ratio[strong] > 1.5)
    assert np.all(np.abs(bad.s_free[sel] - 1) < 0.1)      # a free fit of the same rank is at the noise level everywhere
    assert bad.misfit_regions() and not good.misfit_regions()
    assert np.all(np.abs(good.s_curves[sel] - 1) < 0.1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s_noise = compute_error_scale(xr).s_noise
    assert np.all(np.abs(s_noise[np.isfinite(s_noise)] - 1) < 0.06)


@pytest.mark.fast
def test_error_scale_needs_the_stated_error():
    q, j, M, E, c = _frames(1.0)
    with pytest.raises(ValueError, match="stated error"):
        XrData(M, q, j, E=None).error_scale()
