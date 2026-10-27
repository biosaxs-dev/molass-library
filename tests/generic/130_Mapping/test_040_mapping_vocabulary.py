"""molass-library#331: one vocabulary for mappings, and Decomposition.mapping no longer silently ignores the optimized mapping."""
import warnings

import numpy as np
import pytest

from molass.Mapping.Mapping import Mapping
from molass.LowRank.Decomposition import Decomposition


def test_mapping_has_the_names_of_mappinginfo():
    m = Mapping(1.5, 4.0)
    assert (m.slope, m.intercept) == (1.5, 4.0) == tuple(m)
    assert m.xr_to_uv(10) == m(10) == 19.0
    np.testing.assert_allclose(m.uv_to_xr([4.0, 19.0]), [0.0, 10.0])
    assert m.uv_to_xr(19.0) == m.inv(19.0) == 10.0
    assert "slope=1.5" in repr(m) and "intercept=4" in repr(m)


class _Estimate:
    slope, intercept = 1.4, 3.0

    def __iter__(self):
        return iter((self.slope, self.intercept))


def _decomp(uv_mappings):
    d = Decomposition.__new__(Decomposition)        # only the mapping logic is under test
    d._estimated_mapping = _Estimate()
    d.uv_icurve = object()
    d.uv_ccurves = [type("UvC", (), {"mapping": m})() for m in uv_mappings]
    return d


def test_estimate_only_decomposition_is_silent_and_has_no_optimized_mapping():
    d = _decomp([Mapping(1.4, 3.0), Mapping(1.4, 3.0)])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert d.mapping is d.estimated_mapping
    assert d.optimized_mapping is None
    assert d.get_uv_mapping() is d.estimated_mapping


def test_optimized_mapping_is_exposed_and_mapping_warns():
    opt = Mapping(1.45, 2.0)
    d = _decomp([opt, opt])
    assert d.optimized_mapping is opt and d.get_uv_mapping() is opt
    assert d.estimated_mapping.slope == 1.4
    with pytest.warns(UserWarning, match="optimized mapping") as rec:
        assert d.mapping is d.estimated_mapping
    assert rec[0].filename == __file__
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        d.estimated_mapping     # the explicit name never warns


def test_no_uv_has_no_optimized_mapping():
    d = _decomp([])
    d.uv_icurve = None
    assert d.optimized_mapping is None and d.get_uv_mapping() is None


def test_mapping_can_still_be_assigned():
    d = _decomp([])
    est = _Estimate()
    d.mapping = est
    assert d.estimated_mapping is est
