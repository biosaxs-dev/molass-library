"""molass.LowRank.correct_interparticle (molass-library#414): the interparticle correction of one component on arrays with a selectable method and an Rg
override. Simulated frames with known truth (molass.Testing.interparticle_frames); no local data."""
import warnings

import numpy as np
import pytest

from molass.LowRank import correct_interparticle
from molass.Testing import interparticle_frames, hard_sphere_B, sphere_form_factor

RG = 33.0
R = np.sqrt(5 / 3) * RG


def _curve(nf=160, centre=60.0, s=8.0, tau=14.0):
    from scipy.special import erfc
    j = np.arange(nf, dtype=float)
    c = np.exp(-(j - centre) / tau + s ** 2 / (2 * tau ** 2)) * erfc((s ** 2 - tau * (j - centre)) / (np.sqrt(2) * s * tau))
    return c / c.max()


def _frames(K=0.51, noise_scale=1.0, nq=300, nf=160, seed=0):
    qv = np.linspace(0.01, 0.3, nq)
    A = 0.33 * sphere_form_factor(qv, RG)
    B = hard_sphere_B(qv, A, K, R)
    err = 0.002 * (1 + 0.5 * np.exp(-qv / 0.03))
    return interparticle_frames(A, B, _curve(nf), qv, err, noise_scale=noise_scale, seed=seed, K=K, R_eff=R)


@pytest.fixture(scope="module")
def fr():
    return _frames()


@pytest.mark.parametrize("method", ["soft_bounded", "bounded", "simple", "rank1"])
def test_every_method_returns_a_result_with_the_c_it_used(fr, method):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method=method)
    assert res.method == method and res.A.shape == fr.qv.shape and res.B.shape == fr.qv.shape and res.c_used.shape == fr.c.shape
    assert (np.all(res.B == 0)) == (method == "rank1")
    assert (res.rg is None) == (method in ("simple", "rank1"))
    assert "InterparticleResult" in repr(res)


def test_the_rg_override_reaches_the_bound_and_the_comparison_ranks_the_methods(fr):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        base = correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method="bounded")
        over = correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method="bounded", rg=1.5 * base.rg)
        soft = correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, rg=40.0)
        rank1 = correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method="rank1")
        simple = correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method="simple")
    assert over.rg == pytest.approx(1.5 * base.rg) and over.rg_given and not base.rg_given
    assert soft.rg == 40.0 and soft.info['sigma'] == pytest.approx(2 * np.sqrt(5 / 3) * 40.0)
    low = fr.qv < 0.03
    truth = fr.A[low]
    err = lambda a: np.mean(np.abs(a[low] - truth) / truth)
    assert err(simple.A) < 0.5 * err(rank1.A)                             # the c^2 term corrects the low-q profile


def test_correct_interparticle_equals_the_decomposition_path_for_one_component():
    import molass
    from molass.Testing import simulate_tiny
    molass.set_progress(False)
    d = simulate_tiny().trimmed_copy().corrected_copy().quick_decomposition(num_components=1, proportions=[1])
    d.update_xr_ranks([2])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        P = d.get_xr_matrices()[2]
        c = np.asarray(d.xr_ccurves[0].get_xy()[1], float)
        res = correct_interparticle(d.xr.M, c, d.xr.qv, error=d.xr.E)
    np.testing.assert_allclose(res.A, P[:, 0], rtol=1e-8)


def test_argument_errors_name_the_cause(fr):
    with pytest.raises(ValueError, match="stated error"):
        correct_interparticle(fr.M, fr.c, fr.qv)                          # the default method needs error=
    with pytest.raises(ValueError, match="unknown method"):
        correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method="synthesized")
    with pytest.raises(ValueError, match="shape"):
        correct_interparticle(fr.M, fr.c[:-1], fr.qv, error=fr.E)
    with pytest.raises(ValueError, match="soft_bounded"):
        correct_interparticle(fr.M, fr.c, fr.qv, error=fr.E, method="simple", refine_c=False)
