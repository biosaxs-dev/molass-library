"""
Test RgCurve.i0s / i0_errors (molass-library#322): I(0) of the per-frame Guinier fits next to .rgs.
"""
import numpy as np
from types import SimpleNamespace
from molass.Guinier.RgCurve import RgCurve


def _curve(results):
    n = len(results)
    return RgCurve(np.arange(n), np.linspace(20.0, 30.0, n), np.ones(n), results=results)


def test_010_i0s_and_errors():
    results = [SimpleNamespace(I0=1.5, I0_stdev=0.1), None, SimpleNamespace(I0=2.5, I0_stdev=0.2)]
    curve = _curve(results)
    assert curve.i0s.shape == curve.rgs.shape == (3,)
    np.testing.assert_allclose(curve.i0s, [1.5, np.nan, 2.5])
    np.testing.assert_allclose(curve.i0_errors, [0.1, np.nan, 0.2])


def test_020_missing_error_attribute_gives_nan():
    # e.g. ATSAS results carry I0 but no I0_stdev
    curve = _curve([SimpleNamespace(I0=1.0), SimpleNamespace(I0=2.0)])
    np.testing.assert_allclose(curve.i0s, [1.0, 2.0])
    assert np.all(np.isnan(curve.i0_errors))


def test_030_no_results_gives_nan():
    curve = _curve([None, None])
    curve.results = None
    assert np.all(np.isnan(curve.i0s))
