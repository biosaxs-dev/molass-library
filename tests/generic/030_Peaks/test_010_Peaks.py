"""
    test Peaks
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
from molass.Testing import show_or_save, control_matplotlib_plot

local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

@control_matplotlib_plot
def test_010_Kosugi3a():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20161119", "Kosugi3a_BackSub")
    ssd = SSD(path)
    uv_curve = ssd.uv.get_icurve()
    xr_curve = ssd.xr.get_icurve()

    fig, axes = plt.subplots(ncols=2, figsize=(10,4))
    fig.suptitle("Kosugi3a BackSub")
    for ax, curve, title in zip(axes, [uv_curve, xr_curve], ["UV Curve", "XR Curve"]):
        ax.plot(curve.x, curve.y)
        peaks = curve.get_peaks(num_peaks=2)
        ax.plot(curve.x[peaks], curve.y[peaks], 'o', label='Peaks')
        ax.set_title(title)
        ax.legend()

    fig.tight_layout()
    show_or_save("test_010_Kosugi3a", fig)

@control_matplotlib_plot
def test_020_detect_peaks_return_properties():
    """Issue #36: detect_peaks(return_properties=True) returns prominences."""
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20161119", "Kosugi3a_BackSub")
    ssd = SSD(path)

    # Default call — returns list of int (backward-compatible)
    peaks = ssd.xr.detect_peaks()
    assert isinstance(peaks, list)
    assert all(isinstance(p, int) for p in peaks)
    assert len(peaks) > 0

    # With return_properties=True — returns (list, dict)
    peaks2, props = ssd.xr.detect_peaks(return_properties=True)
    assert peaks2 == peaks, "Peak positions must match regardless of return_properties"
    assert 'prominences' in props
    assert 'peak_heights' in props
    assert len(props['prominences']) == len(peaks)
    assert len(props['peak_heights']) == len(peaks)
    assert np.all(props['prominences'] > 0), "All prominences must be positive"

def test_040_get_recognition_curve():
    """Issue #41: get_recognition_curve() respects elution_recognition option."""
    from molass.DataObjects import SecSaxsData as SSD
    from molass.Global.Options import set_molass_options, get_molass_options
    from molass.DataObjects.Curve import Curve
    path = os.path.join(DATA_ROOT_FOLDER, "20161119", "Kosugi3a_BackSub")
    ssd = SSD(path)

    # Default: 'icurve' — should match get_icurve() values
    assert get_molass_options('elution_recognition') == 'icurve'
    rc_icurve = ssd.xr.get_recognition_curve()
    assert isinstance(rc_icurve, Curve)
    np.testing.assert_array_equal(rc_icurve.y, ssd.xr.get_icurve().y)

    # Switch to 'sum' — should match M.sum(axis=0)
    set_molass_options(elution_recognition='sum')
    rc_sum = ssd.xr.get_recognition_curve()
    assert isinstance(rc_sum, Curve)
    np.testing.assert_array_almost_equal(rc_sum.y, ssd.xr.M.sum(axis=0))

    # detect_peaks() result should differ between modes when data has q-dependent characteristics
    peaks_sum = ssd.xr.detect_peaks()
    set_molass_options(elution_recognition='icurve')
    peaks_icurve = ssd.xr.detect_peaks()
    # Both must return valid non-empty lists; exact equality is dataset-dependent
    assert isinstance(peaks_sum, list) and len(peaks_sum) > 0
    assert isinstance(peaks_icurve, list) and len(peaks_icurve) > 0

@control_matplotlib_plot
def test_030_plot_peaks():
    """Issue #37: XrData.plot_peaks() standalone and axis-injectable."""
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20161119", "Kosugi3a_BackSub")
    ssd = SSD(path)

    # Standalone
    fig, ax = ssd.xr.plot_peaks()
    assert fig is not None
    assert ax is not None
    show_or_save("test_030_plot_peaks_standalone", fig)

    # Axis-injectable
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    fig_ret, ax_ret = ssd.xr.plot_peaks(ax=ax2)
    assert ax_ret is ax2, "Should plot on the provided axes"
    show_or_save("test_030_plot_peaks_injected", fig2)