"""Order-independence of the cached getters of Decomposition (molass-library#300, see also #294).

Whatever sequence of getters ran before, get_rgs() and the P matrix from get_xr_matrices()
must be identical to those of a pristine decomposition.
"""
import itertools
import numpy as np
import pytest
from molass_data import SAMPLE3
from molass.DataObjects import SecSaxsData as SSD

GETTERS = {
    "get_rgs": lambda d: d.get_rgs(),
    "get_guinier_objects": lambda d: d.get_guinier_objects(),
    "get_xr_matrices": lambda d: d.get_xr_matrices(),
    "get_xr_components": lambda d: d.get_xr_components(),
}


def _fresh(ranks):
    d = SSD(SAMPLE3).quick_decomposition()
    if ranks is not None:
        d.update_xr_ranks(ranks)
    return d


def _result(d):
    return np.array(d.get_rgs()), np.array(d.get_xr_matrices()[2])


@pytest.mark.parametrize("ranks", [None, [2, 1, 1]], ids=["rank1", "rank2"])
def test_getters_are_order_independent(ranks):
    ref_rgs, ref_P = _result(_fresh(ranks))
    sequences = [(n,) for n in GETTERS] + list(itertools.permutations(GETTERS, 2))
    for seq in sequences:
        d = _fresh(ranks)
        for name in seq:
            GETTERS[name](d)
        rgs, P = _result(d)
        np.testing.assert_allclose(rgs, ref_rgs, err_msg=f"get_rgs differs after {seq}")
        np.testing.assert_allclose(P, ref_P, err_msg=f"P differs after {seq}")


def test_update_xr_ranks_after_getters_matches_pristine():
    """Getters called under the old ranks must not leak into results under the new ranks."""
    ref_rgs, ref_P = _result(_fresh([2, 1, 1]))
    d = _fresh(None)
    d.get_rgs()
    d.get_xr_components()
    d.update_xr_ranks([2, 1, 1])
    rgs, P = _result(d)
    np.testing.assert_allclose(rgs, ref_rgs)
    np.testing.assert_allclose(P, ref_P)
