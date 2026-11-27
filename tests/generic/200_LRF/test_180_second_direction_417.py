"""The second-direction report (molass-library#417): an interparticle c^2 term, two overlapping species, a clean peak and a baseline ramp, on simulated frames (no local data).
Reference: molass-researcher experiments/67_second_direction/README.md."""
import numpy as np
import pytest

from molass.LowRank.SecondDirection import second_direction_report, SNR2_GATE
from molass.Testing import interparticle_frames, hard_sphere_B, sphere_form_factor

RG = 33.0
R = np.sqrt(5 / 3) * RG


def _curve(nf=160, centre=60.0, s=8.0, tau=14.0):
    from scipy.special import erfc
    j = np.arange(nf, dtype=float)
    c = np.exp(-(j - centre) / tau + s ** 2 / (2 * tau ** 2)) * erfc((s ** 2 - tau * (j - centre)) / (np.sqrt(2) * s * tau))
    return c / c.max()


QV = np.linspace(0.0075, 0.3, 300)
ERR = 0.002 * (1 + 0.5 * np.exp(-QV / 0.03))
C = _curve()
A = 0.33 * sphere_form_factor(QV, RG)


def _noise(shape, scale, seed):
    return scale * np.tile(ERR[:, None], (1, shape[1])) * np.random.default_rng(seed).standard_normal(shape)


def _interparticle(K=0.51, noise_scale=1.0, seed=0):
    fr = interparticle_frames(A, hard_sphere_B(QV, A, K, R), C, QV, ERR, noise_scale=noise_scale, seed=seed, K=K, R_eff=R)
    return fr.M, fr.E


def _species(shift=6, ratio=0.25, noise_scale=1.0, seed=0):
    j = np.arange(len(C), dtype=float)
    c2 = np.interp(j - shift, j, C)
    A2 = 0.33 * sphere_form_factor(QV, 22.0)
    M0 = A[:, None] * C[None, :] + ratio * A2[:, None] * c2[None, :]
    E = np.tile(ERR[:, None], (1, len(C)))
    return M0 + _noise(M0.shape, noise_scale, seed), E


def _clean(seed=0):
    M0 = A[:, None] * C[None, :]
    return M0 + _noise(M0.shape, 1.0, seed), np.tile(ERR[:, None], (1, len(C)))


def _ramp(M, amp):
    half = np.where(C >= 0.5)[0]
    s = np.zeros(len(C))
    s[half] = (np.arange(len(half)) - len(half) / 2) / (len(half) / 2)
    return M + amp * 0.33 * s[None, :]


@pytest.mark.fast
def test_an_interparticle_term_reads_as_a_pure_c2_term():
    r = second_direction_report(QV, *_interparticle())
    t = r['time_side']
    assert r['readable'] and r['snr2'] > SNR2_GATE and r['baseline']['flag'] == 'none'
    assert t['closure_rho_min'] < 0.06 and t['cef'] > 0.9 and abs(t['parity']) < 0.1 and t['hysteresis'] < 1.5


@pytest.mark.fast
def test_a_shifted_second_species_reads_as_another_time_profile():
    r = second_direction_report(QV, *_species())
    t = r['time_side']
    assert r['readable']
    assert t['closure_rho_min'] > 0.15 and t['cef'] < 0.3 and t['parity'] > 0.5 and t['hysteresis'] > 3


@pytest.mark.fast
def test_no_second_direction_is_not_read_and_a_wrong_noise_scale_divides_out():
    r = second_direction_report(QV, *_clean())
    assert not r['readable'] and r['time_side'] == {} and "nothing is read" in repr(r)
    # the stated error 2.5 times too small: the hysteresis is normalised by the noise scale and stays near 1 for a c^2 term
    r2 = second_direction_report(QV, *_interparticle(K=1.0, noise_scale=2.5))
    assert r2['readable'] and r2['time_side']['hysteresis'] < 1.5


@pytest.mark.fast
def test_a_baseline_ramp_is_flagged_and_the_report_says_the_time_side_is_then_unreliable():
    M, E = _interparticle()
    assert second_direction_report(QV, M, E)['baseline']['flag'] == 'none'
    r = second_direction_report(QV, _ramp(M, 0.03), E)
    assert r['baseline']['flag'] == 'likely' and r['baseline']['d3'] < 0.15 and r['baseline']['snr3'] > 2
    assert "baseline" in " ".join(r['notes']) and "correct the baseline first" in repr(r)
    M0 = A[:, None] * C[None, :]                              # a clean peak with a ramp is rank 2: the flat vector is in the top-2 subspace
    r0 = second_direction_report(QV, _ramp(M0, 0.03) + _noise(M0.shape, 1.0, 1), np.tile(ERR[:, None], (1, len(C))))
    assert r0['baseline']['flag'] == 'likely' and r0['baseline']['d2'] < 0.15


@pytest.mark.fast
def test_the_decomposition_method_and_the_argument_errors():
    import molass
    from molass.Testing import simulate_tiny
    molass.set_progress(False)
    d = simulate_tiny().trimmed_copy().corrected_copy().quick_decomposition(num_components=1, proportions=[1])
    r = d.second_direction_report()
    assert set(r) >= {'snr2', 'readable', 'baseline', 'time_side', 'reference', 'window', 'notes'} and "second direction report" in repr(r)
    with pytest.raises(ValueError, match="stated error"):
        second_direction_report(QV, *(_clean()[0], None))
    with pytest.raises(ValueError, match="too small"):
        second_direction_report(QV, _clean()[0][:, :10], np.tile(ERR[:, None], (1, 10)))
    d.xr.E = None
    with pytest.raises(ValueError, match="stated error"):
        d.second_direction_report()
