"""molass-library#332: RgCurve has an informative repr (frame coverage, I(0) availability)."""
from types import SimpleNamespace

import numpy as np

from molass.Guinier.RgCurve import RgCurve


def _results(i0s):
    return [None if v is None else SimpleNamespace(I0=v, I0_stdev=0.1) for v in i0s]


def test_repr_full_curve_with_i0():
    frames = np.arange(1, 11)
    rg = RgCurve(frames, np.full(10, 30.0), np.ones(10), results=_results([1.0] * 10))
    assert repr(rg) == "RgCurve(10 frames 1-10, finite Rg: 10, I(0): 10 finite)"


def test_repr_partial_restored_curve_without_i0():
    # as restored by try_fast_rg_curve: part of the frames, Rg and scores only
    frames = np.arange(69, 181)
    rgs = np.full(len(frames), 30.0)
    rgs[:5] = np.nan
    text = repr(RgCurve(frames, rgs, np.ones(len(frames))))
    assert text == "RgCurve(112 frames 69-180, finite Rg: 107, I(0): not available)"


def test_repr_reports_gaps_and_failed_fits():
    frames = np.array([1, 2, 3, 7, 8])
    rg = RgCurve(frames, np.array([30.0, np.nan, 31.0, 30.5, 30.2]), np.ones(5),
                 results=_results([1.0, None, 1.1, 1.0, None]))
    assert repr(rg) == "RgCurve(5 frames 1-8, 3 frames missing in between, finite Rg: 4, I(0): 3 finite)"


def test_repr_empty():
    assert repr(RgCurve([], np.array([]), np.array([]))) == "RgCurve(empty)"
