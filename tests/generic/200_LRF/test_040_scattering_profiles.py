"""
    Test issue #115: discoverable per-component scattering profile API.

    - ``Decomposition.get_scattering_profiles()`` convenience accessor.
    - ``ComponentCurve`` (returned by ``decomp.xr_components``) does NOT carry P.
    - ``XrComponent`` (returned by ``decomp.get_xr_components()``) does carry P.
"""
import numpy as np
import pytest
from molass import get_version
get_version(toml_only=True)
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.LowRank.ComponentCurve import ComponentCurve
from molass.LowRank.Component import XrComponent


@pytest.fixture(scope="module")
def decomp():
    ssd = SSD(SAMPLE1)
    corrected = ssd.trimmed_copy().corrected_copy()
    corrected.estimate_mapping()
    return corrected.quick_decomposition(num_components=2)


def test_get_scattering_profiles(decomp):
    qv, P, Pe = decomp.get_scattering_profiles()
    n_q = decomp.xr.M.shape[0]
    assert qv.shape == (n_q,)
    assert P.shape == (n_q, decomp.num_components)
    assert Pe.shape == P.shape
    # Same numbers as get_xr_matrices
    _M, _C, P2, Pe2 = decomp.get_xr_matrices()
    np.testing.assert_array_equal(P, P2)
    np.testing.assert_array_equal(Pe, Pe2)
    np.testing.assert_array_equal(qv, decomp.xr.qv)


def test_xr_components_alias_is_elution_only(decomp):
    """xr_components is an alias for xr_ccurves -> ComponentCurve (no P)."""
    comps = decomp.xr_components
    assert comps is decomp.xr_ccurves
    assert all(isinstance(c, ComponentCurve) for c in comps)


def test_get_xr_components_carries_scattering(decomp):
    """get_xr_components() returns XrComponent with j-curve (P)."""
    xrcs = decomp.get_xr_components()
    assert all(isinstance(c, XrComponent) for c in xrcs)
    j = xrcs[0].get_jcurve_array()
    n_q = decomp.xr.M.shape[0]
    assert j.shape == (n_q, 3)  # [q, P, Pe]
