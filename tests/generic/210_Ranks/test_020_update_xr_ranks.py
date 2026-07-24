"""Tests for Decomposition.update_xr_ranks() method

NOTE: Current behavior (as of 2026-07-03):
- update_xr_ranks() accepts any list without validation
- get_xr_matrices() uses fallback: `ranks or [1] * num_components`
- No error is raised for length mismatch

This test documents current behavior. Future enhancement could add validation.
"""
import pytest
from molass_data import SAMPLE3
from molass.DataObjects import SecSaxsData as SSD


def test_update_xr_ranks_sets_attribute():
    """update_xr_ranks sets xr_ranks attribute without validation"""
    ssd3 = SSD(SAMPLE3)
    d = ssd3.quick_decomposition()
    
    # SAMPLE3 has 3 components
    assert d.num_components == 3
    
    # Can set any ranks list (no validation currently)
    d.update_xr_ranks([2])
    assert d.xr_ranks == [2]
    
    d.update_xr_ranks([2, 1, 1])
    assert d.xr_ranks == [2, 1, 1]


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
