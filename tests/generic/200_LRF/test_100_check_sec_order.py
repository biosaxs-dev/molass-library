"""Tests for Decomposition.check_sec_order() (molass-library#296)."""
import numpy as np
import pytest
from molass.LowRank.SecOrder import SecOrderReport, rg_curve_at


class FakeRgCurve:
    def __init__(self, frames, values):
        self.indeces = np.asarray(frames)
        self.rgvalues = np.asarray(values, dtype=float)


def test_report_ordered():
    r = SecOrderReport([60.0, 40.0, 30.0], [100, 150, 200], None, 2.0)
    assert r.ordered and bool(r)
    assert r.violations == []
    assert r.rg_curve_values is None and r.relative_deviations is None
    assert "ordered=True" in repr(r)


def test_report_violation_beyond_tolerance_only():
    ok = SecOrderReport([60.0, 40.0, 41.5], [100, 150, 200], None, 2.0)   # 1.5 A reversal is within tolerance
    assert ok.ordered
    bad = SecOrderReport([60.0, 40.0, 45.0], [100, 150, 200], None, 2.0)
    assert not bad.ordered and not bool(bad)
    assert bad.violations == [(1, 2, pytest.approx(5.0))]
    assert "violation" in repr(bad)


def test_report_nan_rg_is_not_ordered():
    assert not SecOrderReport([60.0, float('nan')], [100, 150], None, 2.0).ordered


def test_rg_curve_values_and_deviations():
    frames = np.arange(0, 300)
    rgc = FakeRgCurve(frames, 100 - 0.2 * frames)        # 100 at frame 0, 40 at frame 300
    assert rg_curve_at(rgc, 150) == pytest.approx(70.0, abs=0.5)
    r = SecOrderReport([70.0, 50.0], [150, 250], [rg_curve_at(rgc, 150), rg_curve_at(rgc, 250)], 2.0)
    assert r.relative_deviations == pytest.approx([0.0, 0.0], abs=0.02)


def test_rg_curve_at_without_data_is_nan():
    assert np.isnan(rg_curve_at(FakeRgCurve([1, 2], [np.nan, np.nan]), 1))


def test_decomposition_check_sec_order_on_sample():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    d = SSD(SAMPLE1).trimmed_copy().corrected_copy().quick_decomposition()
    report = d.check_sec_order()                 # no Rg curve computed
    assert isinstance(report, SecOrderReport)
    assert len(report.rgs) == d.num_components == len(report.positions)
    assert report.rg_curve_values is None
    assert report.ordered == bool(np.all(np.diff(report.rgs) < 2.0))
