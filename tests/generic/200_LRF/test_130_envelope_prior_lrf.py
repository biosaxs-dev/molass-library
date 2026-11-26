"""EP-LRF in molass-library: concentration refinement, whitened SVD denoising, the envelope-prior estimator on arrays and through
Decomposition.set_rank2_method('envelope_prior'). Simulated frames with known truth (molass.Testing.interparticle_frames); no local data needed."""
import warnings

import numpy as np
import pytest

from molass.LowRank.EnvelopePrior import envelope_prior_lrf, EnvelopePriorInfo
from molass.LowRank.ConcentrationRefine import refine_concentration
from molass.LowRank.LowRankInfo import get_denoised_data, get_weighted_denoised_data
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


@pytest.mark.fast
def test_weighted_denoising_equals_plain_for_equal_errors_and_resists_a_noisy_row():
    rng = np.random.default_rng(0)
    U = rng.standard_normal((60, 2)); V = rng.standard_normal((2, 80))
    M0 = 5 * U @ V
    np.testing.assert_allclose(get_weighted_denoised_data(M0, np.ones_like(M0), 2), get_denoised_data(M0, 2), atol=1e-8)
    E = np.ones_like(M0); E[:3] = 40.0                                   # three rows with a 40 times larger error, as the lowest q of real data
    M = M0 + E * rng.standard_normal(M0.shape)
    err_w = np.linalg.norm(get_weighted_denoised_data(M, E, 2)[10:] - M0[10:])
    err_p = np.linalg.norm(get_denoised_data(M, 2)[10:] - M0[10:])
    assert err_w < err_p


@pytest.mark.fast
def test_refinement_repairs_a_distorted_concentration_curve():
    fr = _frames(noise_scale=1.0)
    c_true = fr.c
    j = np.arange(len(c_true), dtype=float)
    c_start = np.interp(60 + (j - 60 - 2.0) / 1.12, j, c_true)             # 12 % too wide and 2 frames late
    ref = refine_concentration(fr.qv, fr.M, fr.E, c_start, q_max=0.1)
    err0 = np.max(np.abs(c_start / c_start.max() - c_true))
    err1 = np.max(np.abs(ref["c"] - c_true))
    assert err1 < 0.5 * err0 and err1 < 0.03
    assert ref["c"].max() == pytest.approx(1.0) and ref["converged"]


@pytest.mark.fast
def test_ep_lrf_is_exact_without_noise_and_shrinks_b_at_high_q_with_noise():
    fr = _frames(noise_scale=0.0)
    E = np.full_like(fr.M, 1e-9)                                           # the stated error is also tiny: s_r << tau at every q
    out = envelope_prior_lrf(fr.qv, fr.M, fr.M, E, fr.c, rg_seed=RG)
    np.testing.assert_allclose(out["A"], fr.A, rtol=1e-6, atol=1e-8)                   # rank 2 exactly: the weights are 1 everywhere
    ok = fr.A > 1e-3 * fr.A.max()                                           # the ratio is ill-conditioned at the zeros of the form factor
    np.testing.assert_allclose(out["r_post"][ok], (fr.B / fr.A)[ok], atol=1e-6)

    fr = _frames(noise_scale=1.0, seed=2)
    out = envelope_prior_lrf(fr.qv, fr.M, get_weighted_denoised_data(fr.M, fr.E, 2), fr.E, fr.c, rg_seed=RG)
    qv = fr.qv
    w = out["tau"] ** 2 / (out["tau"] ** 2 + out["s_r"] ** 2)
    assert np.all((w >= 0) & (w <= 1))
    assert np.max(np.abs(out["r_post"][qv > 0.25])) < 0.02                  # B/A -> 0 at high q (the true value is about 0.001)
    kw = (qv >= 0.018) & (qv < 0.035)
    mean_out = envelope_prior_lrf(fr.qv, fr.M, get_weighted_denoised_data(fr.M, fr.E, 2), fr.E, fr.c, rg_seed=RG, k_rule="mean")
    assert mean_out["K"] == pytest.approx(np.mean(np.abs(fr.B / fr.A)[kw]), rel=0.15)  # 'mean' rule: the mean |B/A| over 0.018-0.035 (not the model K)
    assert out["K"] >= mean_out["K"] * 0.9                                  # 'peak' rule: the largest significant window below 0.035, never much below the mean
    low = (qv >= 0.018) & (qv < 0.04)
    rel = lambda a: np.sqrt(np.mean(((a / a[low].mean()) / (fr.A / fr.A[low].mean()) - 1)[low] ** 2))
    rank1 = np.sum(fr.M * fr.c[None, :], axis=1) / np.sum(fr.c ** 2)
    assert rel(out["A"]) < 0.3 * rel(rank1)                                 # the correction acts where it should


@pytest.mark.fast
def test_set_rank2_method_validation_and_default_is_the_bounded_lrf():
    import molass
    from molass.Testing import simulate_tiny
    molass.set_progress(False)
    corrected = simulate_tiny().trimmed_copy().corrected_copy()
    d = corrected.quick_decomposition(num_components=1, proportions=[1])
    assert d.rank2_method == 'bounded'
    with pytest.raises(ValueError, match="unknown rank-2 method"):
        d.set_rank2_method('shape_model')
    with pytest.raises(ValueError, match="unknown option"):
        d.set_rank2_method('envelope_prior', speed='fast')
    with pytest.raises(ValueError, match="no options"):
        d.set_rank2_method('bounded', L=3)
    d.update_xr_ranks([2])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d.get_xr_matrices()
    assert d.bounded_lrf_info and d.envelope_prior_info is None
    d.set_rank2_method('envelope_prior', warn=False)
    assert d.bounded_lrf_info is None and d.envelope_prior_info is None      # caches are invalidated


@pytest.mark.fast
def test_envelope_prior_through_the_decomposition_corrects_the_low_q_bend():
    import molass
    molass.set_progress(False)
    qv = np.linspace(0.0143, 0.4268, 200)
    c = _curve(120)
    A = 0.33 * sphere_form_factor(qv, RG)
    B = hard_sphere_B(qv, A, 0.51, R)
    fr = interparticle_frames(A, B, c, qv, 0.0006 * (1 + 0.3 * np.exp(-qv / 0.05)), noise_scale=1.0, seed=1, K=0.51, R_eff=R)
    d = fr.to_ssd().trimmed_copy().corrected_copy().quick_decomposition(1)
    qd = d.xr.qv
    a_true, _ = fr.truth_on(qd)
    low = (qd >= 0.018) & (qd < 0.04)
    rel = lambda a: np.sqrt(np.mean(((a / a[low].mean()) / (a_true / a_true[low].mean()) - 1)[low] ** 2))

    err_rank1 = rel(d.get_xr_matrices()[2][:, 0])
    d.update_xr_ranks([2])
    d.set_rank2_method('envelope_prior', warn=False)
    M, C, P, Pe = d.get_xr_matrices()
    info = d.envelope_prior_info[0]
    assert isinstance(info, EnvelopePriorInfo) and d.bounded_lrf_info is None
    assert P.shape == (len(qd), 1) and np.all(np.isfinite(P)) and np.all(np.isfinite(Pe))
    assert rel(P[:, 0]) < 0.5 * err_rank1                                   # rank 1: about 0.2 at this strength
    assert info['c_refined'] is not None and info['c_refined'].max() == pytest.approx(1.0)
    assert 0.2 < info['K'] < 0.9 and 0 <= info['weight_mid'] <= 1
    assert "cutoff_q=" in repr(info) and "<array" in repr(info)
