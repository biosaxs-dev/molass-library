"""
    test SSD
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE1

import pytest
from molass.DataObjects import SecSaxsData as SSD

ssd_instance = SSD(SAMPLE1)

def test_01_constructor():
    assert ssd_instance is not None, "SSD object should not be None"
    assert hasattr(ssd_instance, 'xr'), "SSD object should have 'xr' attribute"
    assert hasattr(ssd_instance, 'uv'), "SSD object should have 'uv' attribute"

def test_02_uv_friendly_aliases():
    uv = ssd_instance.uv
    # wavelengths and frames are human-readable aliases
    import numpy as np
    assert np.array_equal(uv.wavelengths, uv.iv), "wavelengths should equal iv"
    assert np.array_equal(uv.frames, uv.jv), "frames should equal jv"
    assert np.array_equal(uv.wavelengths, uv.wv), "wavelengths should equal wv"
    # M shape should match
    assert uv.M.shape == (len(uv.wavelengths), len(uv.frames)), \
        "M shape should be (wavelengths, frames)"

def test_04_ssd_data_alias():
    xr = ssd_instance.xr
    uv = ssd_instance.uv
    import numpy as np
    # .data should be identical to .M for both XrData and UvData
    assert np.array_equal(xr.data, xr.M), "xr.data should equal xr.M"
    assert np.array_equal(uv.data, uv.M), "uv.data should equal uv.M"

def test_05_repr():
    xr = ssd_instance.xr
    uv = ssd_instance.uv
    xr_repr = repr(xr)
    uv_repr = repr(uv)
    # repr should contain class name and shape info
    assert "iv=" in xr_repr and "jv=" in xr_repr, f"xr repr missing shape info: {xr_repr}"
    assert "wavelengths=" in uv_repr and "frames=" in uv_repr, f"uv repr missing shape info: {uv_repr}"
    assert "nm" in uv_repr, f"uv repr should include wavelength range in nm: {uv_repr}"

def test_06_wavelength_range():
    uv = ssd_instance.uv
    wl_min, wl_max = uv.wavelength_range
    assert wl_min < wl_max, "wavelength_range min should be less than max"
    assert wl_min == uv.wavelengths.min(), "wavelength_range min should match wavelengths.min()"
    assert wl_max == uv.wavelengths.max(), "wavelength_range max should match wavelengths.max()"

def test_03_plot_3d():
    plot_result = ssd_instance.plot_3d()
    assert plot_result is not None, "Plot result should not be None"
    plot_result = ssd_instance.plot_3d(uv_only=True)
    assert plot_result is not None, "Plot result should not be None"
    plot_result = ssd_instance.plot_3d(xr_only=True)
    assert plot_result is not None, "Plot result should not be None"

def test_07_rgcurve_y_is_float_nan():
    """RgCurve.y must be a float array with nan for failed fits — issue #22."""
    import numpy as np
    trimmed   = ssd_instance.trimmed_copy()
    corrected = trimmed.corrected_copy()
    rgcurve   = corrected.xr.compute_rgcurve()
    # y must be a float array, not an object array
    assert rgcurve.y.dtype == float, \
        f"RgCurve.y should be float dtype, got {rgcurve.y.dtype}"
    # failed fits must be nan, not None
    assert None not in rgcurve.y, \
        "RgCurve.y should not contain None (use nan instead)"
    # at least some frames should have valid Rg
    assert np.any(np.isfinite(rgcurve.y) & (rgcurve.y > 0)), \
        "RgCurve.y should contain at least some valid positive Rg values"


def test_08_get_baseline2d_no_stdout(capsys):
    """get_baseline2d() must not print diagnostic messages to stdout — issue #23."""
    trimmed = ssd_instance.trimmed_copy()
    trimmed.xr.get_baseline2d()
    captured = capsys.readouterr()
    assert captured.out == "", \
        f"get_baseline2d() should not print to stdout, got: {captured.out!r}"