"""Tests for Langmuir extension of PoreEntryAnimation.run_simulation."""
import numpy as np
import pytest


def _sim(**kwargs):
    import matplotlib; matplotlib.use('Agg')
    from molass.SEC.PoreEntryAnimation import run_simulation
    kwargs.setdefault('n_steps', 5_000)
    kwargs.setdefault('seed', 77)
    return run_simulation(**kwargs)


def test_wall_bound_zero_when_no_adsorption():
    """k_ads=0 → no wall-adsorbed steps, K_ads_theory=0."""
    s = _sim(k_ads=0.0, k_des=1.0)
    assert s['wall_bound'].sum() == 0
    assert s['K_ads_theory'] == 0.0


def test_wall_bound_nonzero_with_adsorption():
    """k_ads>0 → some wall-adsorbed steps (uses seed=42 that reliably enters pores)."""
    s = _sim(k_ads=3.0, k_des=1.0, n_steps=10_000, seed=42)
    assert s['wall_bound'].sum() > 0


def test_wall_bound_only_inside_pore():
    """wall_bound can only be True when the molecule is in a pore (states >= 0)."""
    s = _sim(k_ads=2.0, k_des=1.0)
    mobile_and_bound = s['wall_bound'] & (s['states'] < 0)
    assert mobile_and_bound.sum() == 0


def test_K_ads_theory():
    """K_ads_theory = k_ads / k_des."""
    k_ads, k_des = 3.0, 2.0
    s = _sim(k_ads=k_ads, k_des=k_des)
    assert abs(s['K_ads_theory'] - k_ads / k_des) < 1e-10


def test_K_eff_theory():
    """K_eff_theory = K_SEC_theory * (1 + K_ads_theory)."""
    k_ads, k_des = 2.0, 1.0
    s = _sim(k_ads=k_ads, k_des=k_des)
    expected = s['K_SEC_theory'] * (1 + s['K_ads_theory'])
    assert abs(s['K_eff_theory'] - expected) < 1e-10


def test_K_eff_greater_than_K_SEC():
    """With adsorption, effective K > geometric K."""
    s_sec = _sim(k_ads=0.0, k_des=1.0)
    s_ads = _sim(k_ads=2.0, k_des=1.0)
    assert s_ads['K_eff_theory'] > s_sec['K_SEC_theory']


def test_mean_dwell_longer_with_adsorption():
    """Adsorption delays exit → longer mean dwell time (statistical test)."""
    s_sec = _sim(n_steps=10_000, k_ads=0.0, k_des=1.0, seed=42)
    s_ads = _sim(n_steps=10_000, k_ads=3.0, k_des=1.0, seed=42)
    if len(s_sec['dwell_times']) > 0 and len(s_ads['dwell_times']) > 0:
        assert s_ads['dwell_times'].mean() > s_sec['dwell_times'].mean()


def test_return_shapes():
    """wall_bound has same length as positions (n_steps+1)."""
    n = 3_000
    s = _sim(n_steps=n, k_ads=1.0, k_des=1.0)
    assert s['wall_bound'].shape == (n + 1,)
    assert s['positions'].shape == (n + 1, 2)
    assert s['states'].shape == (n + 1,)


def test_k_des_zero_yields_inf_K_ads():
    """k_des=0 → K_ads_theory = inf (molecule never desorbs)."""
    s = _sim(k_ads=1.0, k_des=0.0)
    assert s['K_ads_theory'] == float('inf')
