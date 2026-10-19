"""
Mapping.PeakMatcher: peak positions decide the XR/UV correspondence, curve shapes only break ties.

The proteins5 case: XR has 5 peaks and UV has 6 (one UV-only peak at 547); the five XR peaks lie on one
line with UV (603, 696, 812, 890, 937). The EGH-reconstruction correlation used before picked a different
pairing depending on tau_limit.
"""
import numpy as np
import pytest

from molass.DataObjects.Curve import Curve
from molass.Mapping.PeakMatcher import estimate_peak_sigma, select_matching_peaks


def _curve(centers, sigmas, n, heights=None):
    x = np.arange(n)
    heights = heights if heights is not None else [1.0] * len(centers)
    y = sum(h * np.exp(-0.5 * ((x - c) / s) ** 2) for h, c, s in zip(heights, centers, sigmas))
    return Curve(x, y, type='i')


def test_proteins5_like_five_to_five_pairing():
    xr_peaks = [561, 648, 760, 825, 878]
    uv_peaks = [547, 603, 696, 812, 890, 937]
    xr = _curve(xr_peaks, [10] * 5, 1400)
    uv = _curve(uv_peaks, [11] * 6, 1400, heights=[0.4, 1.0, 0.7, 0.9, 0.5, 1.2])
    xr_sel, uv_sel = select_matching_peaks(xr, xr_peaks, uv, uv_peaks)
    assert list(xr_sel) == xr_peaks
    assert list(uv_sel) == [603, 696, 812, 890, 937]


def test_unrelated_extra_peak_is_dropped_not_forced():
    """3 XR vs 3 UV peaks where one XR peak has no UV partner and one UV peak is spurious (EcoCas3-like):
    the 3-peak line fit is off by about one peak width, so a 2-peak pairing must be chosen."""
    xr_peaks = [628, 740, 859]
    uv_peaks = [739, 853, 1277]
    xr = _curve(xr_peaks, [30, 7, 29], 1500)
    uv = _curve(uv_peaks, [14, 32, 19], 1500)
    xr_sel, uv_sel = select_matching_peaks(xr, xr_peaks, uv, uv_peaks)
    assert len(xr_sel) == len(uv_sel) == 2


def test_two_peaks_each_are_kept():
    xr = _curve([88, 157], [7, 8], 300)
    uv = _curve([131, 231], [11, 12], 400)
    xr_sel, uv_sel = select_matching_peaks(xr, [88, 157], uv, [131, 231])
    assert list(xr_sel) == [88, 157] and list(uv_sel) == [131, 231]


def test_fewer_than_two_peaks_passes_through():
    xr = _curve([100], [10], 300)
    uv = _curve([120, 200], [10, 10], 300)
    xr_sel, uv_sel = select_matching_peaks(xr, [100], uv, [120, 200])
    assert list(xr_sel) == [100] and list(uv_sel) == [120]


def test_estimate_peak_sigma():
    c = _curve([200], [12], 400)
    assert estimate_peak_sigma(c, [200]) == pytest.approx(12, rel=0.05)


def test_proteins5_data_default_mapping():
    """proteins5 is bundled as molass_data.SAMPLE6."""
    molass_data = pytest.importorskip("molass_data")
    if not hasattr(molass_data, "SAMPLE6"):
        pytest.skip("installed molass_data has no SAMPLE6 (20191006_proteins5)")
    from molass.DataObjects import SecSaxsData as SSD
    mapping = SSD(molass_data.SAMPLE6).estimate_mapping()
    assert list(mapping.xr_peaks) == [561, 648, 760, 825, 878]
    assert list(mapping.uv_peaks) == [603, 696, 812, 890, 937]
    assert mapping.slope == pytest.approx(1.0636, abs=0.005)
