"""
Test UserWarning for EDM fitted b > 0 (SEC context).

When any per-component b parameter comes out positive after EDM optimization,
optimize_edm_xr_decomposition() should issue a UserWarning explaining the
physical implication (Langmuir adsorption in SEC — usually the wrong mechanism).

The warning can be suppressed via suppress_positive_b_warning=True.

Related: molass-library issue AI-friendliness: warn when EDM fitted b > 0.
"""
import warnings

import numpy as np
import pytest
from molass_legacy.Models.RateTheory.EDM import edm_impl
from molass.SEC.Models.EdmOptimizer import (
    optimize_edm_xr_decomposition,
    _check_positive_b,
)


# ---------------------------------------------------------------------------
# Minimal fakes (same helpers as test_020)
# ---------------------------------------------------------------------------

class _FakeIcurve:
    def __init__(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)

    def get_xy(self):
        return self.x, self.y


class _FakeCurve:
    def __init__(self, x, peak_frame, amplitude=1.0, width=10.0):
        self.x = np.asarray(x, dtype=float)
        self.y = amplitude * np.exp(-0.5 * ((self.x - peak_frame) / width) ** 2)


class _FakeDecomposition:
    def __init__(self, x, y, ccurves):
        self.xr_icurve = _FakeIcurve(x, y)
        self.xr_ccurves = ccurves
        self.num_components = len(ccurves)


def _make_edm_params(t0=100.0, u=1.0, a=1.0, b=0.5, e=0.5, Dz=0.01, cinj=1.0):
    return np.array([t0, u, a, b, e, Dz, cinj])


# ---------------------------------------------------------------------------
# Unit tests for _check_positive_b helper
# ---------------------------------------------------------------------------

def test_check_positive_b_fires_when_positive():
    """_check_positive_b issues UserWarning when b > 0."""
    with pytest.warns(UserWarning, match="b ="):
        _check_positive_b([0.5], suppress=False, stacklevel=2)


def test_check_positive_b_silent_when_nonpositive():
    """_check_positive_b stays quiet when all b ≤ 0."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _check_positive_b([-0.1, 0.0], suppress=False, stacklevel=2)  # must not raise


def test_check_positive_b_suppressed():
    """suppress=True prevents the warning even when b > 0."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _check_positive_b([1.0], suppress=True, stacklevel=2)  # must not raise


def test_check_positive_b_message_content():
    """Warning message names the component index and b value."""
    with pytest.warns(UserWarning, match=r"component\(s\) \[0\]"):
        _check_positive_b([0.75], suppress=False, stacklevel=2)


# ---------------------------------------------------------------------------
# Integration tests via optimize_edm_xr_decomposition (free-EDM path)
# ---------------------------------------------------------------------------
# Use shared_column=False (free-EDM) so we can supply init_params with b > 0
# and the optimizer stays near the positive-b minimum.
# DeprecationWarning for shared_column=False is expected and filtered out.

_SUPPRESSED_DEPR = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@_SUPPRESSED_DEPR
def test_free_edm_warns_when_b_positive():
    """optimize_edm_xr_decomposition issues UserWarning when fitted b > 0 (free-EDM)."""
    x = np.linspace(50, 200, 300)

    # Data generated with b = 0.8 (positive) — optimizer should find b > 0
    p0 = _make_edm_params(t0=80.0, u=1.0, a=1.0, b=0.8, e=0.5, Dz=0.01, cinj=1.0)
    y0 = edm_impl(x, *p0)
    ccurve0 = _FakeCurve(x, float(x[np.argmax(y0)]))
    decomp = _FakeDecomposition(x, y0, [ccurve0])

    init = np.array([p0])  # init already at true params (b=0.8 > 0)

    with pytest.warns(UserWarning, match="b ="):
        optimize_edm_xr_decomposition(decomp, init, shared_column=False)


@_SUPPRESSED_DEPR
def test_free_edm_no_warning_when_b_zero():
    """No UserWarning when fitted b ≤ 0 (free-EDM, b=0 init matches linear data)."""
    x = np.linspace(50, 200, 300)

    # Use b exactly 0 for both data and init — optimizer stays at b=0 (or tiny negative)
    p0 = _make_edm_params(t0=80.0, u=1.0, a=1.0, b=0.0, e=0.5, Dz=0.01, cinj=1.0)
    y0 = edm_impl(x, *p0)
    ccurve0 = _FakeCurve(x, float(x[np.argmax(y0)]))
    decomp = _FakeDecomposition(x, y0, [ccurve0])

    init = np.array([p0])  # init at b=0

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        optimize_edm_xr_decomposition(decomp, init, shared_column=False)


@_SUPPRESSED_DEPR
def test_free_edm_warning_suppressed():
    """suppress_positive_b_warning=True silences the warning (free-EDM)."""
    x = np.linspace(50, 200, 300)

    p0 = _make_edm_params(t0=80.0, u=1.0, a=1.0, b=0.8, e=0.5, Dz=0.01, cinj=1.0)
    y0 = edm_impl(x, *p0)
    ccurve0 = _FakeCurve(x, float(x[np.argmax(y0)]))
    decomp = _FakeDecomposition(x, y0, [ccurve0])

    init = np.array([p0])

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        # Must not raise despite b=0.8 > 0
        optimize_edm_xr_decomposition(
            decomp, init,
            shared_column=False,
            suppress_positive_b_warning=True,
        )
