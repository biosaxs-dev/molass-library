import numpy as np
import pytest

from molass.Guinier.RgCurve import RgCurve


def test_reliable_filters_score_failed_and_sentinel_rg_and_intensity():
    curve = RgCurve(
        [10, 11, 12, 13, 14, 15],
        [30.0, 31.0, 100.0, np.nan, -1.0, 50.0],
        [0.8, 0.59, 0.9, 0.9, 0.9, 0.8],
        score_source="test estimator",
    )

    frames, rgs = curve.reliable()
    np.testing.assert_array_equal(frames, [10, 15])
    np.testing.assert_array_equal(rgs, [30.0, 50.0])

    frames, rgs = curve.reliable(intensity=[100.0, 100.0, 100.0, 100.0, 100.0, 4.0])
    np.testing.assert_array_equal(frames, [10])
    np.testing.assert_array_equal(rgs, [30.0])


def test_reliable_returns_empty_for_all_missing_intensities():
    curve = RgCurve([2, 3], [20.0, 21.0], [0.9, 0.8])
    frames, rgs = curve.reliable(intensity=[np.nan, np.nan])
    assert len(frames) == len(rgs) == 0


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"score_min": 1.1}, "score_min"),
        ({"intensity_frac": -0.1}, "intensity_frac"),
        ({"intensity": [1.0]}, "aligned with frames"),
    ],
)
def test_reliable_rejects_invalid_thresholds_and_misaligned_intensity(kwargs, message):
    curve = RgCurve([1, 2], [20.0, 21.0], [0.9, 0.8])
    with pytest.raises(ValueError, match=message):
        curve.reliable(**kwargs)


def test_repr_identifies_score_source():
    curve = RgCurve([1], [30.0], [0.8], score_source="ATSAS Autorg Quality (0-1)")
    assert "scores: ATSAS Autorg Quality (0-1)" in repr(curve)
