"""molass-library#390: photon-counting error model of Sedlak et al. (2017) for simulated SAXS data."""
from functools import partial

import numpy as np
import pytest

from molass.Kratky import FormFactors as ff
from molass.SAXS.ErrorModel import sedlak_sigma, add_sedlak_noise, SYNCHROTRON, IN_HOUSE
from molass.Testing.Simulator import Species, simulate_ssd

Q = np.linspace(0.01, 0.4, 400)
P = ff.sphere_P(Q, 27.0)


def test_sigma_follows_the_formula_of_the_paper():
    scale, k, c, q_arb = 100.0, 4500.0, 0.85, 0.2
    I = 0.07*P                                          # arbitrary units
    counts = I*scale/I[0]
    i_arb = np.interp(q_arb, Q, counts)
    expected = np.sqrt((counts + 2*c*i_arb/(1 - c))/(k*Q))*I[0]/scale          # eq. 10, back in the units of I
    assert sedlak_sigma(I, Q, scale=scale, k=k, c=c, q_arb=q_arb) == pytest.approx(expected)
    assert sedlak_sigma(I, Q) == pytest.approx(expected)                       # the defaults are the synchrotron values
    assert SYNCHROTRON["scale"] == 100.0 and IN_HOUSE["c"] == 0.90


def test_relative_error_scales_with_the_inverse_square_root_of_the_counts_and_not_with_the_units():
    r100 = sedlak_sigma(P, Q, scale=100.0)/P
    r25 = sedlak_sigma(P, Q, scale=25.0)/P
    assert r25 == pytest.approx(2*r100)
    assert sedlak_sigma(1000*P, Q) == pytest.approx(1000*sedlak_sigma(P, Q))


def test_the_error_grows_relative_to_the_signal_at_large_q():
    r = sedlak_sigma(P, Q)/P
    assert r[np.searchsorted(Q, 0.05)] < 0.03             # a few percent at small angles for 100 counts
    assert r[np.searchsorted(Q, 0.3)] > 5*r[np.searchsorted(Q, 0.05)]           # the constant buffer term dominates


def test_sec_matrix_shares_the_buffer_term_and_follows_each_frame():
    frames = np.stack([P, 0.1*P, 0*P], axis=1)
    s = sedlak_sigma(frames, Q)
    assert s.shape == frames.shape
    assert s[:, 0] == pytest.approx(sedlak_sigma(P, Q))                   # the strongest frame equals the 1-D result
    to_counts = 100.0/P[0]
    # sigma^2 of two frames differs by the signal term only: (I1 - I2) / (to_counts k q) in the units of I
    assert (s[:, 0]**2 - s[:, 1]**2) == pytest.approx((0.9*P)/(to_counts*4500.0*Q))
    assert np.all(s[:, 2] > 0)                                            # the buffer noise remains where there is no signal


def test_averaging_buffer_frames_lowers_the_buffer_term():
    empty = np.stack([P, 0*P], axis=1)
    b1 = sedlak_sigma(empty, Q, n_buffer=1)[:, 1]**2
    b2 = sedlak_sigma(empty, Q, n_buffer=2)[:, 1]**2
    assert b2 == pytest.approx(0.75*b1)                    # (1 + 1/2) / (1 + 1)


def test_added_noise_has_the_standard_deviation_sigma():
    frames = np.repeat(P[:, None], 2000, axis=1)
    noisy, sigma = add_sedlak_noise(frames, Q, seed=3)
    z = (noisy - frames)/sigma
    assert abs(z.mean()) < 0.01
    assert z.std() == pytest.approx(1.0, abs=0.01)
    again, _ = add_sedlak_noise(frames, Q, seed=3)
    assert np.array_equal(noisy, again)                     # reproducible


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        sedlak_sigma(P, Q[:-1])
    with pytest.raises(ValueError):
        sedlak_sigma(P, Q, c=1.0)
    with pytest.raises(ValueError):
        sedlak_sigma(P, Q, scale=0)
    with pytest.raises(ValueError):
        sedlak_sigma(P, Q, n_buffer=0)
    with pytest.raises(ValueError):
        sedlak_sigma(0*P, Q)
    with pytest.raises(ValueError):
        sedlak_sigma(P, Q - 0.02)                            # a q value <= 0


def _small_ssd(**kwargs):
    q = np.linspace(0.02, 0.4, 150)
    species = [Species(amp=1.0, center=40.0, sigma=6.0, mass=0.05, rg=25.0)]
    return simulate_ssd(species, qv=q, wv=np.linspace(250.0, 400.0, 20), xr_frames=np.arange(80),
                        uv_frames=np.arange(3, 150), seed=2, **kwargs)


def test_simulate_ssd_with_the_error_model_uses_sigma_as_noise_and_stated_error():
    ssd = _small_ssd(xr_error_model="sedlak")
    E = ssd.xr.E
    assert E.shape == ssd.xr.M.shape
    assert E[:, 40].mean() > E[:, 0].mean()                  # the error follows the intensity of each frame
    clean = _small_ssd(xr_error_model="sedlak", noise=0.0).xr.M
    z = (ssd.xr.M - clean)/E
    assert z.std() == pytest.approx(1.0, abs=0.03)
    ssd30 = _small_ssd(xr_error_model=partial(sedlak_sigma, scale=30.0))
    assert ssd30.xr.E[:, 40].mean() > ssd.xr.E[:, 40].mean()                 # fewer counts, larger error


def test_error_model_excludes_the_fixed_sigma_options():
    with pytest.raises(ValueError):
        _small_ssd(xr_error_model="sedlak", xr_sigma=0.01)
    with pytest.raises(ValueError):
        _small_ssd(xr_error_model=lambda I, q: np.ones(5))
