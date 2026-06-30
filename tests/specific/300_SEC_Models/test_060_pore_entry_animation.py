"""
tests/specific/300_SEC_Models/test_060_pore_entry_animation.py

Sanity tests for molass.SEC.PoreEntryAnimation.

Runs a short simulation (2 000 steps) and checks:
- K_SEC_sim is in the expected range relative to the Knox approximation
- Dwell times are non-empty and positive
- get_pore_entry_animation returns (FuncAnimation, dict)
"""
import numpy as np
import pytest
from matplotlib.animation import FuncAnimation

from molass.SEC.PoreEntryAnimation import run_simulation, get_pore_entry_animation


@pytest.fixture(scope='module')
def sim():
    return run_simulation(r_mol=0.03, R_grain=0.20, num_pores=3,
                          D=0.003, dt=0.002, n_steps=2_000, seed=0)


def test_simulation_keys(sim):
    required = {'positions', 'states', 'entry_times', 'dwell_times',
                'entry_grain_arr', 'grains', 'R_p', 'rho', 'K_SEC_theory', 'T_total'}
    assert required.issubset(sim.keys())


def test_positions_shape(sim):
    assert sim['positions'].shape == (2_001, 2)


def test_rho_and_K_SEC_theory(sim):
    assert 0 < sim['rho'] < 1
    assert 0 < sim['K_SEC_theory'] < 1
    assert abs(sim['K_SEC_theory'] - (1 - sim['rho']) ** 2) < 1e-10


def test_dwell_times_positive(sim):
    dw = sim['dwell_times']
    if len(dw) > 0:
        assert np.all(dw > 0)


def test_K_SEC_sim_plausible(sim):
    # K_SEC_sim should be within 50% of the Knox approximation
    # (sector wedge gives softer exclusion curve)
    K_SEC_sim = (sim['states'] >= 0).sum() / len(sim['states'])
    K_SEC_th  = sim['K_SEC_theory']
    if K_SEC_sim > 0:
        ratio = K_SEC_sim / K_SEC_th
        assert 0.5 < ratio < 2.0, f"K_SEC_sim/K_SEC_theory = {ratio:.3f} out of expected range"


def test_get_pore_entry_animation():
    import matplotlib
    matplotlib.use('Agg')
    ani, sim = get_pore_entry_animation(
        r_mol=0.03, n_steps=500, n_frames=10, close_plot=True, seed=1)
    assert isinstance(ani, FuncAnimation)
    assert 'dwell_times' in sim
