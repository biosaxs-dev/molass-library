"""
Trimming.AnomalyHandler: an irregular UV end (dip below the baseline in the last frames) is excluded from
the trimming and the XR/UV mapping (20200123_3). Data without it must not be affected.
"""
import os
import warnings

import numpy as np
import pytest

from molass.DataObjects.Curve import Curve
from molass.Global.Options import get_molass_options, set_molass_options
from molass.Trimming.AnomalyHandler import (
    baseline_tilt, cut_uv_end_anomaly, estimate_mapping_handling_anomaly, find_uv_end_anomaly, locate_trailing_dip)

N = 800


def _gauss(center, sigma, height):
    x = np.arange(N)
    return height * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def _noise(seed=0, scale=0.005):
    return np.random.default_rng(seed).normal(0, scale, N)


def _uv_with_dip(depth=0.075, start=764):
    y = _gauss(629, 22, 0.2) + _noise()
    x = np.arange(N)
    dip = np.zeros(N)
    tail = np.arange(start, N)
    dip[tail] = -depth * np.sin(np.pi * (tail - start) / (N - start))
    return Curve(x, y + dip, type='i')


def test_locates_the_start_of_a_trailing_dip():
    y = np.asarray(_uv_with_dip().y)
    assert 755 <= locate_trailing_dip(y) <= 770


def test_no_dip_in_clean_curve():
    assert locate_trailing_dip(_gauss(629, 22, 0.2) + _noise()) is None


def test_trailing_bump_is_not_a_dip():
    """A late elution peak is a real signal, not an anomaly."""
    assert locate_trailing_dip(_gauss(629, 22, 0.2) + _gauss(770, 10, 0.1) + _noise()) is None


def test_dip_in_the_middle_is_ignored():
    y = _gauss(300, 22, 0.2) + _noise()
    y[500:530] -= 0.08
    assert locate_trailing_dip(y) is None


def test_long_dip_is_not_cut():
    """A dip spanning more than MAX_DIP_FRACTION of the frames is not treated as an end anomaly."""
    y = _gauss(300, 22, 0.2) + _noise()
    y[600:] -= 0.08
    assert locate_trailing_dip(y) is None


def test_detection_needs_a_falling_baseline_as_well():
    """The dip alone is not enough; the gate is the baseline tilt (a rising drift must not trigger it)."""
    rising = Curve(np.arange(N), _gauss(629, 22, 0.2) + _noise() + np.linspace(0, 0.1, N), type='i')
    assert baseline_tilt(rising) < 0
    assert find_uv_end_anomaly(rising) is None
    assert find_uv_end_anomaly(Curve(np.arange(N), _gauss(629, 22, 0.2) + _noise(), type='i')) is None


def test_dip_gives_a_positive_tilt_and_is_found():
    curve = _uv_with_dip()
    assert baseline_tilt(curve) > 0.2
    assert 755 <= find_uv_end_anomaly(curve) <= 770


class _Data:
    def __init__(self, curve):
        self._curve = curve

    def get_icurve(self):
        return self._curve


class _Ssd:
    def __init__(self, xr_curve, uv_curve):
        self.xr = _Data(xr_curve)
        self.uv = _Data(uv_curve)


def test_cut_leaves_normal_data_alone():
    uv = Curve(np.arange(N), _gauss(629, 22, 0.2) + _noise(), type='i')
    xr = Curve(np.arange(N), _gauss(563, 12, 0.05) + _noise(1, 0.002), type='i')
    jslice = slice(499, 781)
    assert cut_uv_end_anomaly(_Ssd(xr, uv), jslice) == jslice


def test_cut_shortens_the_uv_slice_at_the_anomaly_without_touching_the_mapping():
    uv = _uv_with_dip()
    xr = Curve(np.arange(N), _gauss(563, 12, 0.05) + _noise(1, 0.002), type='i')
    with warnings.catch_warnings():
        warnings.simplefilter("error")            # the mapping side warns; the cut itself is silent
        jslice = cut_uv_end_anomaly(_Ssd(xr, uv), slice(499, 781))
        assert cut_uv_end_anomaly(_Ssd(xr, uv), slice(499, None)).stop == jslice.stop
    assert jslice.start == 499 and 755 <= jslice.stop <= 770


def test_mapping_is_the_plain_estimation_without_an_anomaly():
    from molass.Mapping.SimpleMapper import estimate_mapping_impl
    uv = Curve(np.arange(N), _gauss(629, 22, 0.2) + _noise(), type='i')
    xr = Curve(np.arange(N), _gauss(563, 12, 0.05) + _noise(1, 0.002), type='i')
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        handled = estimate_mapping_handling_anomaly(xr, uv)
    plain = estimate_mapping_impl(xr, uv)
    assert (handled.slope, handled.intercept) == (plain.slope, plain.intercept)


def test_mapping_excludes_the_anomaly_and_keeps_the_full_curve():
    uv = _uv_with_dip()
    xr = Curve(np.arange(N), _gauss(563, 12, 0.05) + _noise(1, 0.002), type='i')
    with pytest.warns(UserWarning, match="irregular end"):
        mapping = estimate_mapping_handling_anomaly(xr, uv)
    assert mapping.uv_curve is uv and mapping.slope > 0


def test_option_is_on_by_default():
    assert get_molass_options('anomaly_handling') is True


def test_20200123_3_mapping_and_trimming():
    from molass.Local import get_local_settings
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(get_local_settings()['DATA_ROOT_FOLDER'], "20200123_3")
    if not os.path.exists(path):
        pytest.skip("20200123_3 is not available")

    # the mapping estimation itself is anomaly-aware, not only the trimming
    with pytest.warns(UserWarning, match="irregular end"):
        direct = SSD(path).estimate_mapping()
    assert direct.slope == pytest.approx(1.05, abs=0.02)

    ssd = SSD(path)
    with pytest.warns(UserWarning, match="irregular end"):
        trimmed = ssd.trimmed_copy()
    mapping = ssd.get_mapping()
    assert mapping.slope == pytest.approx(1.05, abs=0.02)
    assert trimmed.uv.jv[-1] < 765

    set_molass_options(anomaly_handling=False)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)    # no anomaly warning when switched off
            SSD(path).trimmed_copy()
    finally:
        set_molass_options(anomaly_handling=True)
