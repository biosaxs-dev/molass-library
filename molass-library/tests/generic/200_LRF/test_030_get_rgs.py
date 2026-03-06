"""
Tests for Decomposition.get_rgs() — issue #8.

Verifies that get_rgs() never returns None: when Guinier fitting fails
(sv.Rg is None), float('nan') must be returned instead.
"""
import math
import pytest
from unittest.mock import MagicMock, patch
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used


def make_guinier_stub(rg_value):
    """Return a minimal Guinier object stub with Rg set to *rg_value*."""
    stub = MagicMock()
    stub.Rg = rg_value
    return stub


def test_010_get_rgs_returns_nan_when_guinier_fails():
    """get_rgs() must return float('nan') instead of None on Guinier failure."""
    from molass.LowRank.Decomposition import Decomposition

    decomp = Decomposition.__new__(Decomposition)
    decomp.guinier_objects = [
        make_guinier_stub(12.5),   # successful fit
        make_guinier_stub(None),   # failed fit
    ]

    rgs = decomp.get_rgs()

    assert rgs[0] == pytest.approx(12.5)
    assert math.isnan(rgs[1]), "Expected float('nan') for failed Guinier, got: {!r}".format(rgs[1])


def test_020_get_rgs_no_none_in_result():
    """get_rgs() result must never contain None."""
    from molass.LowRank.Decomposition import Decomposition

    decomp = Decomposition.__new__(Decomposition)
    decomp.guinier_objects = [make_guinier_stub(v) for v in (15.0, None, 8.3, None)]

    rgs = decomp.get_rgs()

    assert None not in rgs, "get_rgs() must not return None values"
    assert all(isinstance(v, float) for v in rgs), "All values must be float"


def test_030_get_rgs_all_valid():
    """get_rgs() passes through valid Rg values unchanged."""
    from molass.LowRank.Decomposition import Decomposition

    decomp = Decomposition.__new__(Decomposition)
    decomp.guinier_objects = [make_guinier_stub(v) for v in (10.0, 20.0)]

    rgs = decomp.get_rgs()

    assert rgs == pytest.approx([10.0, 20.0])
