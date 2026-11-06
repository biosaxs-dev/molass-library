from types import SimpleNamespace

import numpy as np

from molass.Guinier.RgCurve import RgCurve
from molass.LowRank.Decomposition import Decomposition


class _FakeSsd:
    def __init__(self):
        self.xr = SimpleNamespace(
            M=np.arange(12.0).reshape(3, 4),
            qv=np.array([0.01, 0.02, 0.03]),
            jv=np.arange(4),
            E=np.ones((3, 4)),
        )
        self.trimming = SimpleNamespace(
            small_angle_limit="extended",
            xr_slices=(slice(0, 3), slice(0, 4)),
        )
        self.computations = 0

    def get_rg_curve(self, progress_cb=None):
        self.computations += 1
        results = [SimpleNamespace(I0=float(i + 1), I0_stdev=0.1) for i in range(4)]
        return RgCurve(np.arange(4), np.arange(20.0, 24.0), np.full(4, 0.8), results=results,
                       score_source="test estimator")


def _decomposition(ssd, cache_path):
    decomp = Decomposition.__new__(Decomposition)
    decomp.ssd = ssd
    decomp._rg_curve_cache_path = str(cache_path)
    return decomp


def test_rg_curve_cache_round_trips_and_invalidates_changed_data(tmp_path):
    ssd = _FakeSsd()
    cache_path = tmp_path / "cache" / "rgcurve.npz"

    first = _decomposition(ssd, cache_path).get_rg_curve()
    cached_decomposition = _decomposition(ssd, cache_path)
    restored = cached_decomposition.get_rg_curve()
    assert ssd.computations == 1
    np.testing.assert_array_equal(restored.frames, first.frames)
    np.testing.assert_array_equal(restored.rgs, first.rgs)
    np.testing.assert_array_equal(restored.scores, first.scores)
    np.testing.assert_array_equal(restored.i0s, first.i0s)
    np.testing.assert_array_equal(restored.i0_errors, first.i0_errors)
    assert restored.score_source == first.score_source

    cached_decomposition.get_rg_curve(refresh=True)
    assert ssd.computations == 2
    ssd.xr.M[0, 0] += 1
    refreshed = _decomposition(ssd, cache_path).get_rg_curve()
    assert ssd.computations == 3
    np.testing.assert_array_equal(refreshed.rgs, first.rgs)
