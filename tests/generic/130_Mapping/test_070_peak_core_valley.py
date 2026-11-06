"""molass-library#368: the core of a small peak next to a large one must stop at the valley between them.

EcoCas3 (3 XR / 3 UV peaks) got slope 0.133 instead of 0.958 because the core of the small peaks (the contiguous
region above half their height) ran into the large neighbour and dragged the sub-frame centroid (#328) toward it.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from molass.Mapping.SimpleMapper import estimate_mapping_for_matching_peaks, peak_position_with_sd, refine_peak_position


def _two_peaks(x, small_c, big_c, small_a=0.5, small_s=5.0, big_s=10.0):
    return small_a * np.exp(-0.5 * ((x - small_c) / small_s) ** 2) + np.exp(-0.5 * ((x - big_c) / big_s) ** 2)


def test_small_peak_on_the_shoulder_of_a_large_one_keeps_its_own_position():
    x = np.arange(200.0)
    rng = np.random.default_rng(0)
    y = _two_peaks(x, 95.0, 120.0) + 0.002 * rng.standard_normal(x.shape)
    apex = int(np.argmax(np.where(np.abs(x - 95) < 8, y, -np.inf)))
    # the valley (~105) stays above half the height of the small peak, so the plain core ran into the large peak
    assert refine_peak_position(x, y, apex) > apex + 10         # unguarded: dragged toward the large peak
    assert refine_peak_position(x, y, apex, max_shift=11.0) == pytest.approx(apex, abs=2.0)
    big = int(np.argmax(y))
    assert refine_peak_position(x, y, big, max_shift=11.0) == pytest.approx(big, abs=2.0)


def test_guard_leaves_ordinary_peaks_unchanged():
    x = np.arange(300.0)
    y = np.exp(-0.5 * ((x - 100.0) / 8.0) ** 2) + np.exp(-0.5 * ((x - 200.0) / 8.0) ** 2)
    for c in (100, 200):
        assert refine_peak_position(x, y, c, max_shift=12.0) == refine_peak_position(x, y, c)
        assert refine_peak_position(x, y, c, max_shift=12.0) == pytest.approx(float(c), abs=1e-6)
    # an asymmetric (tailing) peak moves its centroid by a fraction of its width only: not touched either
    tail = np.where(x < 100, np.exp(-0.5 * ((x - 100.0) / 6.0) ** 2), np.exp(-0.5 * ((x - 100.0) / 12.0) ** 2))
    assert refine_peak_position(x, tail, 100, max_shift=12.0) == refine_peak_position(x, tail, 100)


def test_mapping_of_the_ecocas3_like_case_is_near_identity_not_collapsed():
    # a small peak on the shoulder of a large one in XR only (in UV it is the taller of the two), plus a lone peak;
    # true mapping UV = 0.958 XR + 30. The plain core drags the small XR centroid ~20 frames toward the large peak.
    rng = np.random.default_rng(1)
    xf = np.arange(300.0)
    uf = np.arange(300.0)
    uv_c = lambda c: 0.958 * c + 30.0
    lone = lambda x, c, a, s: a * np.exp(-0.5 * ((x - c) / s) ** 2)
    xr_y = _two_peaks(xf, 95.0, 120.0) + lone(xf, 40.0, 0.5, 6.0)
    uv_y = (_two_peaks(uf, uv_c(95.0), uv_c(120.0), small_a=1.5, small_s=5.0 * 0.958, big_s=10.0 * 0.958)
            + lone(uf, uv_c(40.0), 0.3, 6.0 * 0.958))
    xr = SimpleNamespace(x=xf, y=xr_y + 0.003 * rng.standard_normal(xf.shape))
    uv = SimpleNamespace(x=uf, y=uv_y + 0.003 * rng.standard_normal(uf.shape))
    pick = lambda c, centres: [int(np.argmax(np.where(np.abs(c.x - cc) < 4, c.y, -np.inf))) for cc in centres]
    m = estimate_mapping_for_matching_peaks(xr, pick(xr, (40, 95, 120)), uv, pick(uv, (uv_c(40), uv_c(95), uv_c(120))))
    assert m.slope == pytest.approx(0.958, abs=0.05)
    assert m.intercept == pytest.approx(30.0, abs=8.0)
