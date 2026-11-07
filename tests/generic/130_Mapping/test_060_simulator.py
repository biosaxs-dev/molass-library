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


# molass-library#373: species shapes and continuum_species

def _guinier_rg(shape, rg, shape_arg=None):
    from molass.Testing.Simulator import shape_profile
    q = np.linspace(0.002, 0.8 / rg, 40)
    slope = np.polyfit(q ** 2, np.log(shape_profile(shape, rg, q, shape_arg)), 1)[0]
    return np.sqrt(-3 * slope)


@pytest.mark.parametrize("shape, arg", [("sphere", None), ("ellipsoid", 3.0), ("ellipsoid", 5.0), ("cylinder", 10.0), ("chain", None)])
def test_shape_profiles_have_the_requested_rg(shape, arg):
    assert _guinier_rg(shape, 35.0, arg) == pytest.approx(35.0, rel=0.04)


def test_callable_shape_and_unknown_shape():
    from molass.Testing.Simulator import shape_profile
    q = np.linspace(0.01, 0.3, 5)
    np.testing.assert_allclose(shape_profile(lambda q, rg: np.exp(-(q * rg) ** 2 / 3), 30.0, q), np.exp(-(q * 30.0) ** 2 / 3))
    with pytest.raises(ValueError, match="unknown shape"):
        shape_profile("cube", 30.0, q)


def test_default_species_is_still_a_sphere():
    from molass.Testing.Simulator import clean_signals, sphere, QV
    I, _ = clean_signals([Species(amp=1.0, center=90, sigma=8, mass=1.0, rg=25.0)])
    expected = sphere(QV, 25.0)[:, None] * Species(amp=1.0, center=90, sigma=8, mass=1.0, rg=25.0).elution(np.arange(241))[None, :]
    np.testing.assert_allclose(I, expected)


def test_continuum_species_reproduces_the_hand_built_continuum_of_51r():
    from molass.Testing import continuum_species
    centres = np.linspace(60, 140, 40)
    env = np.exp(-0.5 * ((centres - 95.0) / 22.0) ** 2)
    hand_amp = 2.0 / (6.0 * np.sqrt(2 * np.pi) / np.diff(centres)[0]) * env
    hand_rg = 30.0 + (25.0 - 30.0) * (centres - centres[0]) / (centres[-1] - centres[0])
    sp = continuum_species(30.0, 25.0, 60, 140, envelope=lambda c: np.exp(-0.5 * ((c - 95.0) / 22.0) ** 2))
    np.testing.assert_allclose([s.amp for s in sp], hand_amp)
    np.testing.assert_allclose([s.rg for s in sp], hand_rg)
    np.testing.assert_allclose([s.center for s in sp], centres)


def test_continuum_species_summed_elution_height_follows_the_height_argument():
    from molass.Testing import continuum_species
    f = np.arange(0, 241, dtype=float)
    for n in (20, 40, 60):
        sp = continuum_species(30.0, 25.0, 60, 140, n=n, height=3.0)
        total = sum(s.elution(f) for s in sp)
        assert total.max() == pytest.approx(3.0, rel=0.05)


def test_continuum_species_shape_parameter_changes_along_the_elution():
    from molass.Testing import continuum_species
    sp = continuum_species(30.0, 25.0, 60, 140, n=5, shape="ellipsoid", shape_arg_start=1.5, shape_arg_end=4.5)
    assert [s.shape_arg for s in sp] == pytest.approx([1.5, 2.25, 3.0, 3.75, 4.5])
    assert all(s.shape == "ellipsoid" for s in sp)
