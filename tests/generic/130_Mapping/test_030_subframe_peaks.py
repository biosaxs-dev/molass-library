"""molass-library#328: the mapping is fitted through sub-frame peak positions, not integer apex indices."""
from types import SimpleNamespace

import numpy as np
import pytest

from molass.Mapping.SimpleMapper import estimate_mapping_for_matching_peaks, refine_peak_position

SLOPE, ICPT = 1.4493, 3.464
CENTERS, SIGMA = (90.0, 165.0), 8.0


def _curves(seed, noise=0.02):
    rng = np.random.default_rng(seed)
    xf, uf = np.arange(241.0), np.arange(3.0, 352.0)
    xr_y = sum(np.exp(-0.5 * ((xf - c) / SIGMA) ** 2) for c in CENTERS)
    uv_y = sum(np.exp(-0.5 * (((uf - ICPT) / SLOPE - c) / SIGMA) ** 2) for c in CENTERS)
    xr = SimpleNamespace(x=xf, y=xr_y + noise * rng.standard_normal(xf.shape))
    uv = SimpleNamespace(x=uf, y=uv_y + noise * rng.standard_normal(uf.shape))
    return xr, uv


def _apexes(curve):
    # the apex index near each true peak, as the peak recognition would give
    return [int(np.argmax(np.where(np.abs(curve.x - c) < 20, curve.y, -np.inf))) for c in
            ((c for c in CENTERS) if curve.x[0] == 0 else (SLOPE * c + ICPT for c in CENTERS))]


def test_refined_position_is_sub_frame_on_a_clean_peak():
    x = np.arange(200.0)
    for center in (80.0, 80.3, 80.5, 80.8):
        y = np.exp(-0.5 * ((x - center) / SIGMA) ** 2)
        assert refine_peak_position(x, y, int(np.argmax(y))) == pytest.approx(center, abs=0.02)


def test_refined_position_falls_back_to_the_apex_at_the_edge_or_for_a_thin_core():
    x = np.arange(50.0)
    edge = np.exp(-0.5 * (x / 6.0) ** 2)          # the core is cut by the curve start
    assert refine_peak_position(x, edge, 0) == 0.0
    spike = np.zeros(50)
    spike[20] = 1.0
    assert refine_peak_position(x, spike, 20) == 20.0


def test_mapping_through_refined_positions_is_much_better_than_a_frame():
    shifts = []
    for seed in range(10):
        xr, uv = _curves(seed)
        m = estimate_mapping_for_matching_peaks(xr, _apexes(xr), uv, _apexes(uv))
        shifts.append(((m.slope - SLOPE) * 127 + (m.intercept - ICPT)) / SLOPE)   # XR-frame shift at mid frame
    assert np.sqrt(np.mean(np.square(shifts))) < 0.15
    assert np.max(np.abs(shifts)) < 0.3


def test_peak_indices_stay_integer_apexes():
    xr, uv = _curves(0)
    xr_peaks, uv_peaks = _apexes(xr), _apexes(uv)
    m = estimate_mapping_for_matching_peaks(xr, xr_peaks, uv, uv_peaks)
    assert list(m.xr_peaks) == xr_peaks and list(m.uv_peaks) == uv_peaks
