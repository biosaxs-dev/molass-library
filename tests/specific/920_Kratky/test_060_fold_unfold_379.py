"""
molass-library#379: folded/unfolded form factors, species shapes solved for a requested Rg, the instrument options
of simulate_ssd and the SAMPLE4-like simulated data.
"""
import warnings

import numpy as np
import pytest

from molass.Kratky import FormFactors as ff
from molass.Testing import Species, simulate_ssd, tail_shape, fold_unfold_shape, simulate_sample4_like, sample4_like_species
from molass.Testing.Simulator import SIGMA_XR, clean_signals, QV, WV, XR_FRAMES, UV_FRAMES, SLOPE, INTERCEPT


def _extrapolated_rg(P, q):
    # 3 (1 - P) / q^2 = Rg^2 (1 + O(q^2)), extrapolated linearly in q^2 to q = 0
    slope, intercept = np.polyfit(q**2, 3.0*(1.0 - P)/q**2, 1)
    return np.sqrt(intercept)


@pytest.mark.parametrize("n_chains", [1, 3])
@pytest.mark.parametrize("nonpenetrating", [True, False])
@pytest.mark.parametrize("phi", [0.1, 0.35])
def test_sphere_chains_rg_is_the_small_q_limit_of_the_form_factor(phi, nonpenetrating, n_chains):
    q = np.linspace(0.003, 0.012, 10)
    P = ff.sphere_chains_P(q, 26.0, 16.0, phi, n_chains, nonpenetrating)
    assert _extrapolated_rg(P, q) == pytest.approx(ff.sphere_chains_Rg(26.0, 16.0, phi, n_chains, nonpenetrating), abs=0.01)


def test_sphere_chains_limits():
    q = np.array([0.01, 0.1, 0.3])
    assert ff.sphere_chains_P(q, 27.0, 18.0, 0.0) == pytest.approx(ff.sphere_P(q, 27.0))      # no tail: the sphere
    assert ff.sphere_chains_Rg(27.0, 18.0, 0.0) == pytest.approx(ff.sphere_Rg(27.0))
    assert ff.sphere_chains_P(np.array([1e-4]), 27.0, 18.0, 0.3)[0] == pytest.approx(1.0, abs=1e-5)


def test_fold_unfold_mix():
    q = np.linspace(0.003, 0.012, 10)
    assert _extrapolated_rg(ff.fold_unfold_P(q, 20.0, 55.0, 0.5), q) == pytest.approx(ff.fold_unfold_Rg(20.0, 55.0, 0.5), abs=0.1)
    assert ff.fold_unfold_Rg(20.0, 55.0, 0.0) == pytest.approx(20.0)
    assert ff.fold_unfold_Rg(20.0, 55.0, 1.0) == pytest.approx(55.0)


@pytest.mark.parametrize("make, rg", [(tail_shape(), 24.0), (tail_shape(), 30.0), (fold_unfold_shape(), 35.0)])
def test_species_shape_has_the_requested_rg(make, rg):
    q = np.linspace(0.003, 0.012, 10)
    assert _extrapolated_rg(make(q, rg), q) == pytest.approx(rg, abs=0.1)


def test_species_shape_rejects_an_unreachable_rg():
    with pytest.raises(ValueError):
        tail_shape()(QV, 10.0)
    with pytest.raises(ValueError):
        fold_unfold_shape(20.0, 55.0)(QV, 60.0)


def test_simulate_ssd_defaults_are_unchanged():
    species = [Species(amp=1.0, center=100, sigma=8, mass=2.0, rg=30.0)]
    ssd = simulate_ssd(species, noise=1.0, seed=3)
    I, A = clean_signals(species, 0.0, SLOPE, INTERCEPT, QV, WV, XR_FRAMES, UV_FRAMES)
    rng = np.random.default_rng(3)
    expected = I + 1.0*SIGMA_XR*rng.standard_normal(I.shape)
    assert np.array_equal(ssd.xr.M, expected)
    assert np.all(ssd.xr.E == SIGMA_XR)
    assert ssd.trimmed


def test_simulate_ssd_error_and_scatter_options():
    species = [Species(amp=1.0, center=100, sigma=8, mass=2.0, rg=30.0)]
    sigma = np.linspace(1e-3, 3e-3, len(QV))
    ratio = np.where(np.arange(len(QV)) < 5, 0.0, 1.0)
    ssd = simulate_ssd(species, noise=1.0, seed=3, xr_sigma=sigma, xr_noise_ratio=ratio, trimmed=False)
    I, _ = clean_signals(species, 0.0, SLOPE, INTERCEPT, QV, WV, XR_FRAMES, UV_FRAMES)
    assert not ssd.trimmed
    assert np.allclose(ssd.xr.E[:, 0], sigma)
    assert np.array_equal(ssd.xr.M[:5], I[:5])                      # no scatter where the ratio is 0
    assert np.std(ssd.xr.M[5:] - I[5:]) > 0.5*np.median(sigma)


def test_sample4_like_tails3_truth_and_geometry():
    species = sample4_like_species("tails3")
    assert [s.center for s in species] == [81.0, 95.0, 115.0]
    assert [s.rg for s in species] == [28.6, 26.7, 25.1]
    ssd = simulate_sample4_like("tails3", noise=1.0, seed=0)
    assert ssd.xr.M.shape == (773, 220) and ssd.uv.M.shape == (318, 442)
    assert not ssd.trimmed
    assert 0.065 < ssd.xr.M[10:20].mean(axis=0).max() < 0.085          # peak height near the 0.078 of the real data
    with pytest.raises(ValueError):
        sample4_like_species("nonsense")


def test_sample4_like_loads_with_default_trimming_and_decomposes_into_three_components():
    ssd = simulate_sample4_like("tails3", noise=1.0, seed=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        corrected = ssd.trimmed_copy().corrected_copy()
        decomp = corrected.quick_decomposition(num_components=3, rgcurve=corrected.get_rg_curve(), proportions=[1]*3)
    peaks = [c.peak_index for c in decomp.get_xr_components()]
    assert all(abs(p - t) <= 5 for p, t in zip(peaks, (81, 95, 115)))
    rgs = decomp.get_rgs()
    assert rgs[0] > rgs[1] > rgs[2]                                    # Rg falls with the elution, not collapsed to one value
