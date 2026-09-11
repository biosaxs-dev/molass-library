"""
Tests for LkmEstimator._k_mt_floor and its use as an init-time clamp
(molass-library/Copilot/refactor/DESIGN_lkm_mass_transfer_floor.md).
"""
import pytest
from molass.SEC.Models.LkmEstimator import _k_mt_floor, _k_MT_from_kappa2

# Real SAMPLE5 comp0 values (analysis-007-equivalent EGH seed) that motivated this fix.
T0, PE, R = 434.99, 12008.88, 1.1065


def test_floor_is_positive_for_realistic_params():
    assert _k_mt_floor(T0, R, PE) > 0


def test_floor_matches_manual_formula():
    tol = 1.5
    expected = (R - 1.0) * PE / ((tol**2 - 1.0) * T0 * R**2)
    assert _k_mt_floor(T0, R, PE, tolerance=tol) == pytest.approx(expected)


def test_floor_decreases_as_tolerance_increases():
    floors = [_k_mt_floor(T0, R, PE, tolerance=m) for m in [1.2, 1.5, 2.0, 3.0]]
    assert floors == sorted(floors, reverse=True)


def test_clamp_raises_a_below_floor_estimate():
    # A pathologically broad seed (large kappa2) makes _k_MT_from_kappa2 return
    # a small k_MT -- confirm the max(...) clamp used in estimate_lkm_init_params
    # would lift it back to the floor.
    tR = T0 * R
    huge_kappa2 = 2 * tR**2 / PE + 50.0  # dispersion term + a large kinetics term
    raw_k_mt = _k_MT_from_kappa2(T0, PE, tR, huge_kappa2)
    floor = _k_mt_floor(T0, R, PE)
    assert raw_k_mt < floor
    assert max(raw_k_mt, floor) == floor
