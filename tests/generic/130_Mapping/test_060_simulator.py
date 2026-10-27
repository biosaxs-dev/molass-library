"""molass-library#340: molass.Testing.simulate_ssd, a known-truth SEC-SAXS simulator."""
import numpy as np
import pytest

from molass.Testing import Species, simulate_ssd

SPECIES = [Species(amp=1.0, center=90, sigma=8, mass=1.0, rg=25.0),
           Species(amp=1.0, center=165, sigma=8, mass=2.0, rg=40.0, na=0.3)]


def _shift(mapping, truth, frame=127.0):
    """Equivalent XR-frame shift of ``mapping`` against the truth at ``frame``."""
    (s, b), (s0, b0) = tuple(mapping), tuple(truth)
    return ((s - s0) * frame + (b - b0)) / s0


def test_simulated_ssd_has_the_sample1_geometry_and_carries_its_truth():
    ssd = simulate_ssd(SPECIES, uv_late=0.7, seed=3)
    assert ssd.xr.M.shape == (984, 241) and ssd.uv.M.shape == (254, 349)
    assert ssd.xr.jv[0] == 0 and ssd.uv.jv[0] == 3
    truth = ssd.simulation_truth
    assert truth.species == SPECIES and truth.uv_late == 0.7
    slope, intercept = truth.mapping
    assert truth.true_mapping == pytest.approx((slope, intercept + slope * 0.7))


def test_same_seed_same_data_and_noise_scale():
    a, b = simulate_ssd(SPECIES, seed=1), simulate_ssd(SPECIES, seed=1)
    np.testing.assert_array_equal(a.xr.M, b.xr.M)
    clean = simulate_ssd(SPECIES, noise=0)
    noisy = simulate_ssd(SPECIES, noise=1, seed=1)
    assert np.std(noisy.xr.M - clean.xr.M) == pytest.approx(0.02, rel=0.05)
    assert np.std(simulate_ssd(SPECIES, noise=2, seed=1).xr.M - clean.xr.M) == pytest.approx(0.04, rel=0.05)


def test_the_estimated_mapping_recovers_the_truth_to_a_fraction_of_a_frame():
    for seed, uv_late in ((0, 0.0), (1, 0.0), (2, 1.0)):
        ssd = simulate_ssd(SPECIES, uv_late=uv_late, seed=seed)
        m = ssd.estimate_mapping()
        assert abs(_shift(m, ssd.simulation_truth.true_mapping)) < 0.25
        assert m.resolution_frames is not None and m.resolution_frames < 0.25


def test_noise_free_mapping_is_nearly_exact():
    ssd = simulate_ssd(SPECIES, uv_late=0.5, noise=0)
    assert abs(_shift(ssd.estimate_mapping(), ssd.simulation_truth.true_mapping)) < 0.05
