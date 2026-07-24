"""Tests for Decomposition.update_xr_ranks() method"""
import pytest
from molass_data import SAMPLE3
from molass.DataObjects import SecSaxsData as SSD


def test_update_xr_ranks_sets_attribute():
    """update_xr_ranks sets ranks when length matches num_components"""
    ssd3 = SSD(SAMPLE3)
    d = ssd3.quick_decomposition()

    assert d.num_components == 3

    d.update_xr_ranks([2, 1, 1])
    assert d.xr_ranks == [2, 1, 1]


def test_update_xr_ranks_raises_on_length_mismatch():
    """update_xr_ranks raises ValueError when ranks length != num_components"""
    ssd3 = SSD(SAMPLE3)
    d = ssd3.quick_decomposition()

    assert d.num_components == 3

    with pytest.raises(ValueError, match="Length of ranks"):
        d.update_xr_ranks([2])  # length 1 != num_components 3


def test_get_xr_matrices_with_ranks():
    """get_xr_matrices returns correct shapes when ranks are set"""
    ssd3 = SSD(SAMPLE3)
    d = ssd3.quick_decomposition()
    
    # Set ranks for all components
    d.update_xr_ranks([1, 1, 1])
    M, C, P, Pe = d.get_xr_matrices()
    
    # P shape: (n_q, n_components) where n_components=3
    assert P.shape[1] == 3
    assert Pe.shape[1] == 3
    
    # n_q from SAMPLE3 XR data
    assert P.shape[0] == M.shape[0]
