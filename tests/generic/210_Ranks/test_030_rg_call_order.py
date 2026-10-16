"""Regression tests for molass-library#294: Rg values must not depend on API call order
when rank-2 components (Bounded LRF) are present."""
import numpy as np
from molass_data import SAMPLE3
from molass.DataObjects import SecSaxsData as SSD

RANKS = [2, 1, 1]


def _fresh_decomposition():
    d = SSD(SAMPLE3).quick_decomposition()
    assert d.num_components == 3
    d.update_xr_ranks(RANKS)
    return d


def test_get_rgs_independent_of_call_order():
    """get_rgs() must give the same values whether or not get_xr_matrices() ran first."""
    rgs_direct = np.array(_fresh_decomposition().get_rgs())

    d = _fresh_decomposition()
    d.get_xr_matrices()
    rgs_after_matrices = np.array(d.get_rgs())

    d = _fresh_decomposition()
    d.get_xr_components()
    rgs_after_components = np.array(d.get_rgs())

    np.testing.assert_allclose(rgs_after_matrices, rgs_direct)
    np.testing.assert_allclose(rgs_after_components, rgs_direct)


def test_get_xr_matrices_is_idempotent():
    """Repeated get_xr_matrices() calls (with get_rgs() in between) must return the same P."""
    d = _fresh_decomposition()
    P1 = d.get_xr_matrices()[2].copy()
    d.get_rgs()
    P2 = d.get_xr_matrices()[2]
    np.testing.assert_allclose(P2, P1)


def test_cached_guinier_objects_match_corrected_P():
    """The cached Rgs must be those of the Bounded-LRF-corrected P, not of the naive seed."""
    from molass.Guinier.RgEstimator import RgEstimator

    d = _fresh_decomposition()
    M, C, P, Pe = d.get_xr_matrices()
    qv = d.xr.qv
    expected = [RgEstimator(np.array([qv, P[:, i], Pe[:, i]]).T).Rg for i in range(d.num_components)]
    np.testing.assert_allclose(d.get_rgs(), expected)
