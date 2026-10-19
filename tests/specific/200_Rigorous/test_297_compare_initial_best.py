"""molass-library#297: RunInfo.compare_initial_best() puts the initial and best decompositions side by side."""
import numpy as np
import pytest

from molass.Rigorous.RunInfo import RunInfo


class _Curve:
    def __init__(self, pos):
        self.pos = pos

    def get_peak_position(self):
        return self.pos


class _Decomp:
    def __init__(self, rgs, positions, ordered):
        self._rgs = rgs
        self.xr_ccurves = [_Curve(p) for p in positions]
        self._ordered = ordered
        self.rgcurve_seen = "unset"

    def get_rgs(self):
        return self._rgs

    def check_sec_order(self, rgcurve=None):
        self.rgcurve_seen = rgcurve
        return self._ordered


class _Optimizer:
    def objective_func(self, params, return_full=False):
        assert return_full
        return -1.0, np.zeros(3)


def _make(optimizer=None, init_params=None):
    info = RunInfo.__new__(RunInfo)
    info.optimizer = optimizer
    info.init_params = init_params
    info.rgcurve = "RGCURVE"
    info.decomposition = _Decomp([120.0, 66.0, 82.0], [580.0, 620.0, 650.0], False)
    best = _Decomp([124.0, 87.0, 76.0], [572.0, 601.0, 639.0], True)
    best.sv, best.fv = 78.5, -1.41
    info.load_best = lambda timeout=0, **kw: (setattr(info, '_loaded_job', '007'), best)[1]
    return info


def test_compare_initial_best_both_stages():
    info = _make(_Optimizer(), np.array([1.0, 2.0]))
    cmp = info.compare_initial_best()

    assert cmp['initial']['rgs'] == [120.0, 66.0, 82.0]
    assert cmp['initial']['sec_ordered'] is False
    assert cmp['initial']['fv'] == -1.0
    from molass.Rigorous.CurrentStateUtils import fv_to_sv
    assert cmp['initial']['sv'] == pytest.approx(fv_to_sv(-1.0))
    assert cmp['best']['rgs'] == [124.0, 87.0, 76.0]
    assert cmp['best']['sec_ordered'] is True
    assert cmp['best']['peak_positions'] == [572.0, 601.0, 639.0]
    assert cmp['best']['sv'] == 78.5 and cmp['best']['fv'] == -1.41
    assert cmp['best']['job'] == '007'
    assert info.decomposition.rgcurve_seen == "RGCURVE"


def test_compare_initial_best_without_optimizer():
    """After reconnect()/restore() the objective may be unavailable: sv/fv are None, the rest still works."""
    cmp = _make().compare_initial_best()
    assert cmp['initial']['sv'] is None and cmp['initial']['fv'] is None
    assert cmp['initial']['rgs'] == [120.0, 66.0, 82.0]
