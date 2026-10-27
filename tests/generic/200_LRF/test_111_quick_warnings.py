"""molass-library#321: quick_decomposition must not silently return fewer components or a degenerate one."""
import warnings

import numpy as np
import pytest

from molass.LowRank.ComponentCurve import ComponentCurve
from molass.LowRank.QuickImplement import warn_on_suspicious_components

X = np.arange(200, dtype=float)


def _curves(*heights):
    return [ComponentCurve(X, [h, 60 + 40*i, 8.0, 0.0]) for i, h in enumerate(heights)]


def test_fewer_components_than_requested_warns():
    with pytest.warns(UserWarning, match=r"num_components=4\) returned 3") as rec:
        warn_on_suspicious_components(4, _curves(1.0, 0.8, 0.9))
    assert "proportions=[1]*4" in str(rec[0].message)


def test_requested_count_or_none_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_on_suspicious_components(3, _curves(1.0, 0.8, 0.9))
        warn_on_suspicious_components(None, _curves(1.0, 0.8, 0.9))


def test_non_positive_area_warns():
    with pytest.warns(UserWarning, match="non-positive or negligible"):
        warn_on_suspicious_components(3, _curves(1.0, -1e-4, 0.9))


def test_negligible_area_warns():
    with pytest.warns(UserWarning, match=r"component\(s\) \[2\]"):
        warn_on_suspicious_components(3, _curves(1.0, 1e-5, 0.9))


def test_negative_peaks_allowed_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_on_suspicious_components(3, _curves(1.0, -0.5, 0.9), allow_negative=True)


@pytest.fixture(scope="module")
def ssd():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    return SSD(SAMPLE1).trimmed_copy().corrected_copy()


def test_sample1_num_components_4_warns_at_the_callers_line(ssd):
    with pytest.warns(UserWarning, match="returned 3 components") as rec:
        decomp = ssd.quick_decomposition(num_components=4)
    assert decomp.get_num_components() == 3
    assert rec[0].filename == __file__


def test_sample1_pinned_positions_warn_about_degenerate_component(ssd):
    with pytest.warns(UserWarning, match="non-positive or negligible") as rec:
        decomp = ssd.quick_decomposition(xr_peakpositions=[80, 89, 111, 157])
    assert decomp.get_num_components() == 4
    assert rec[0].filename == __file__


def test_sample1_proportional_four_components_is_silent(ssd):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        decomp = ssd.quick_decomposition(num_components=4, proportions=[1, 1, 1, 1])
    assert decomp.get_num_components() == 4
