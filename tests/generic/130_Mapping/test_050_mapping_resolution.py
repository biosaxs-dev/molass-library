"""molass-library#333 (peak frames vs indices) and #337 (mapping resolution)."""
import numpy as np

from molass.Mapping.SimpleMapper import estimate_mapping_for_matching_peaks, peak_position_with_sd
from test_030_subframe_peaks import SLOPE, ICPT, _curves, _apexes


def test_peak_frames_are_frame_numbers_and_peaks_are_indices():
    xr, uv = _curves(0)
    xr_peaks, uv_peaks = _apexes(xr), _apexes(uv)
    m = estimate_mapping_for_matching_peaks(xr, xr_peaks, uv, uv_peaks)
    np.testing.assert_array_equal(m.xr_peak_frames, xr.x[xr_peaks])
    np.testing.assert_array_equal(m.uv_peak_frames, uv.x[uv_peaks])
    assert uv.x[0] == 3 and not np.array_equal(m.uv_peak_frames, uv_peaks)    # UV frames start at 3


def test_resolution_frames_predicts_the_actual_error():
    actual, predicted = [], []
    for seed in range(10):
        xr, uv = _curves(seed)
        m = estimate_mapping_for_matching_peaks(xr, _apexes(xr), uv, _apexes(uv))
        actual.append(((m.slope - SLOPE) * 127 + (m.intercept - ICPT)) / SLOPE)
        predicted.append(m.resolution_frames)
    rms = np.sqrt(np.mean(np.square(actual)))
    assert 0.5 * rms < np.mean(predicted) < 2.5 * rms
    assert "resolution_frames=" in repr(m)


def test_resolution_grows_with_noise():
    res = []
    for noise in (0.01, 0.04):
        xr, uv = _curves(0, noise=noise)
        res.append(estimate_mapping_for_matching_peaks(xr, _apexes(xr), uv, _apexes(uv)).resolution_frames)
    assert res[1] > 2 * res[0]


def test_peak_position_sd_falls_back_to_half_a_spacing():
    x = np.arange(50.0)
    spike = np.zeros(50)
    spike[20] = 1.0
    assert peak_position_with_sd(x, spike, 20) == (20.0, 0.5)
