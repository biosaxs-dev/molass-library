"""molass-library#415: molass.Testing generator for interparticle frames with known truth (A, B, c) and a stated-level noise."""
import numpy as np
import pytest

from molass.Testing import (interparticle_frames, hard_sphere_B, sphere_form_factor, debye_form_factor, ellipsoid_form_factor,
                            scale_axes_to_rg, effective_radius)
from molass.DataObjects.XrData import XrData

QV = np.linspace(0.01, 0.3, 300)


def _c(nf=160):
    from scipy.special import erfc
    j = np.arange(nf, dtype=float)
    s, tau = 8.0, 14.0
    c = np.exp(-(j - 60) / tau + s ** 2 / (2 * tau ** 2)) * erfc((s ** 2 - tau * (j - 60)) / (np.sqrt(2) * s * tau))
    return c / c.max()


@pytest.mark.fast
def test_form_factors_and_effective_radius():
    q = np.array([1e-6, 0.01])
    rg = 33.0
    for P in (sphere_form_factor(q, rg), debye_form_factor(q, rg)):
        assert P[0] == pytest.approx(1.0, abs=1e-6)
        assert P[1] == pytest.approx(1 - (q[1] * rg) ** 2 / 3, abs=2e-3)               # Guinier
    R = np.sqrt(5 / 3) * rg
    ax = scale_axes_to_rg((1.0, 1.0, 1.0), rg)
    assert ax[0] == pytest.approx(R)                                                    # a sphere of radius sqrt(5/3) Rg
    np.testing.assert_allclose(ellipsoid_form_factor(QV, ax, n_orient=500), sphere_form_factor(QV, rg), atol=2e-3)
    assert effective_radius(ax) == pytest.approx(R, rel=2e-3)                         # V_ex = 32 pi R^3 / 3 for a sphere
    assert effective_radius(scale_axes_to_rg((5, 1, 1), rg)) / R == pytest.approx(0.70, abs=0.01)     # f = 0.70 of experiment 64c


@pytest.mark.fast
def test_frames_are_a_c_plus_b_c2_and_noise_is_at_the_stated_scale():
    c = _c()
    A = 0.33 * sphere_form_factor(QV, 33.0)
    B = hard_sphere_B(QV, A, K=0.255, R_eff=np.sqrt(5 / 3) * 33.0)
    assert hard_sphere_B(np.array([1e-6]), np.array([2.0]), 0.255, 42.6)[0] == pytest.approx(-0.255 * 2.0, rel=1e-3)     # Phi(0) = 1
    assert np.all(B[:20] < 0)
    err = 0.004 * (1 + 0.5 * np.exp(-QV / 0.03))
    clean = interparticle_frames(A, B, c, QV, err, noise_scale=0.0)
    np.testing.assert_allclose(clean.M, A[:, None] * c[None, :] + B[:, None] * (c ** 2)[None, :])
    fr = interparticle_frames(A, B, c, QV, err, noise_scale=1.0, seed=3)
    assert fr.E.shape == fr.M.shape and fr.K is None
    z = (fr.M - clean.M) / fr.E
    assert abs(z.std() - 1) < 0.02
    again = interparticle_frames(A, B, c, QV, err, noise_scale=1.0, seed=3)
    np.testing.assert_array_equal(fr.M, again.M)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = XrData(fr.M, QV, fr.jv, E=fr.E).error_scale().s_noise
    assert np.all(np.abs(s[np.isfinite(s)] - 1) < 0.08)                                 # the estimate of #416 sees noise_scale = 1


@pytest.mark.fast
def test_truth_on_another_grid_for_functions_and_arrays():
    c = _c()
    fA = lambda q: 0.33 * sphere_form_factor(q, 33.0)
    fB = lambda q: hard_sphere_B(q, fA(q), 0.255, 42.6)
    fr = interparticle_frames(fA, fB, c, QV, 0.004, K=0.255, R_eff=42.6)
    sub = QV[40:200:7]
    a, b = fr.truth_on(sub)
    np.testing.assert_allclose(a, fA(sub)); np.testing.assert_allclose(b, fB(sub))
    arr = interparticle_frames(fA(QV), fB(QV), c, QV, 0.004)
    a2, b2 = arr.truth_on(sub)
    np.testing.assert_allclose(a2, fA(sub), rtol=2e-3)
    with pytest.raises(ValueError):
        interparticle_frames(fA(QV)[:-1], fB(QV), c, QV, 0.004)


@pytest.mark.fast
def test_frames_to_ssd_run_the_pipeline_and_the_truth_is_recoverable():
    import molass
    molass.set_progress(False)
    qv = np.linspace(0.0143, 0.4268, 200)
    c = _c(120)
    A = 0.33 * sphere_form_factor(qv, 33.0)
    B = hard_sphere_B(qv, A, K=0.255, R_eff=np.sqrt(5 / 3) * 33.0)
    fr = interparticle_frames(A, B, c, qv, 0.0006 * (1 + 0.3 * np.exp(-qv / 0.05)), noise_scale=1.0, seed=1)
    ssd = fr.to_ssd()
    assert ssd.xr.M.shape == fr.M.shape and ssd.uv is not None
    d = ssd.trimmed_copy().corrected_copy().quick_decomposition(1)
    qd = d.xr.qv
    a_true, _ = fr.truth_on(qd)
    assert len(qd) >= 150 and np.all(np.isfinite(a_true))
    A_lib = d.get_xr_matrices()[2][:, 0]                                                # rank 1 (no correction)
    low = (qd >= 0.018) & (qd < 0.04)
    assert np.mean(np.abs(A_lib[low] / A_lib[low].mean() - a_true[low] / a_true[low].mean())) < 0.3
