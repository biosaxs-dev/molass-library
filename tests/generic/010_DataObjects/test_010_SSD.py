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


def test_09_buffit_baseline():
    """'buffit' method returns a baseline with positive_ratio lower than 'linear' — issue #24."""
    import numpy as np

    def _positive_ratio_mean(M):
        """Mean fraction of positive intensities across all frames, simple unweighted."""
        return np.mean(M > 0)

    trimmed = ssd_instance.trimmed_copy()

    # linear baseline (adaptive p_final)
    trimmed.xr.baseline_method = 'linear'
    b_linear = trimmed.xr.get_baseline2d()
    ratio_linear = _positive_ratio_mean(trimmed.xr.M - b_linear)

    # buffit baseline
    trimmed.xr.baseline_method = 'buffit'
    b_buffit = trimmed.xr.get_baseline2d()
    ratio_buffit = _positive_ratio_mean(trimmed.xr.M - b_buffit)

    assert b_buffit.shape == trimmed.xr.M.shape, \
        "buffit baseline shape should match M"
    assert ratio_buffit < ratio_linear, \
        f"buffit positive_ratio ({ratio_buffit:.3f}) should be lower than linear ({ratio_linear:.3f})"


def test_10_buffit_otsu():
    """Otsu adaptive threshold (default) is at least as good as fixed threshold=0.10 — issue #25."""
    import numpy as np
    from molass.Baseline.BuffitBaseline import BUFFIT_THRESHOLD

    def _positive_ratio_mean(M):
        return np.mean(M > 0)

    trimmed = ssd_instance.trimmed_copy()
    trimmed.xr.baseline_method = 'buffit'

    # Otsu (default: threshold=None)
    b_otsu = trimmed.xr.get_baseline2d()
    ratio_otsu = _positive_ratio_mean(trimmed.xr.M - b_otsu)

    # Fixed threshold=0.10
    b_fixed = trimmed.xr.get_baseline2d(threshold=BUFFIT_THRESHOLD)
    ratio_fixed = _positive_ratio_mean(trimmed.xr.M - b_fixed)

    assert b_otsu.shape == trimmed.xr.M.shape, \
        "Otsu buffit baseline shape should match M"
    assert ratio_otsu <= ratio_fixed + 0.01, \
        f"Otsu positive_ratio ({ratio_otsu:.3f}) should be no worse than fixed ({ratio_fixed:.3f})"


def test_11_q_values_frame_indices_aliases():
    """SsMatrixData.q_values and .frame_indices are aliases for iv and jv — issue #28."""
    import numpy as np
    xr = ssd_instance.xr
    # read aliases
    assert np.array_equal(xr.q_values, xr.iv), "q_values should equal iv"
    assert np.array_equal(xr.frame_indices, xr.jv), "frame_indices should equal jv"
    # setter: modify via alias, check original
    orig_iv = xr.iv.copy()
    xr.q_values = orig_iv * 2
    assert np.array_equal(xr.iv, orig_iv * 2), "setting q_values should update iv"
    xr.q_values = orig_iv  # restore


def test_12_get_bpo_ideal():
    """SsMatrixData.get_bpo_ideal() returns dataset-relative ideal positive_ratio — issue #29."""
    xr = ssd_instance.xr
    bpo_ideal = xr.get_bpo_ideal()
    assert isinstance(bpo_ideal, float), f"bpo_ideal should be float, got {type(bpo_ideal)}"
    assert 0 < bpo_ideal < 1, f"bpo_ideal should be in (0, 1), got {bpo_ideal}"
    # SAMPLE1 is a well-behaved dataset; bpo_ideal should be well above 0.5
    assert bpo_ideal > 0.5, f"SAMPLE1 bpo_ideal should be > 0.5, got {bpo_ideal}"


def test_13_lpm_baseline_mask():
    """compute_lpm_baseline supports mask parameter for frame exclusion — issue #30."""
    import numpy as np
    from molass.Baseline.LpmBaseline import compute_lpm_baseline
    xr = ssd_instance.xr
    x = xr.jv.astype(float)
    y = xr.M[0, :]  # first q-row

    # Without mask
    bl_full, params_full = compute_lpm_baseline(x, y, return_also_params=True)
    assert bl_full.shape == x.shape, "baseline should have same shape as x"

    # With mask: exclude middle 20% of frames
    n = len(x)
    mask = np.ones(n, dtype=bool)
    mask[n//3 : 2*n//3] = False
    bl_masked, params_masked = compute_lpm_baseline(x, y, return_also_params=True, mask=mask)

    # Masked baseline still covers ALL frames
    assert bl_masked.shape == x.shape, "masked baseline should have same shape as x"
    # Slopes should differ (different fitting data)
    assert params_full['slope'] != params_masked['slope'], \
        "masked and unmasked slopes should differ when peak region is excluded"


def test_14_get_snr_weights():
    """get_snr_weights() returns per-q-row SNR array — issue #38."""
    import numpy as np
    xr = ssd_instance.trimmed_copy().xr
    w = xr.get_snr_weights()
    assert w.shape == (len(xr.iv),), f"shape should be (n_q,), got {w.shape}"
    assert (w >= 0).all(), "weights must be non-negative"
    assert w.sum() > 0, "weights should not all be zero"
    # Low-q rows should generally have higher SNR than high-q rows
    n_q = len(w)
    assert w[:n_q // 4].mean() > w[-n_q // 4:].mean(), \
        "low-q SNR should exceed high-q SNR on average"


def test_15_get_positive_ratio():
    """get_positive_ratio() returns SNR-weighted positive_ratio — issue #38."""
    import numpy as np
    xr = ssd_instance.trimmed_copy().xr
    bl = xr.get_baseline2d()

    pr_snr = xr.get_positive_ratio(bl)                     # default = 'snr'
    pr_uni = xr.get_positive_ratio(bl, weighting='uniform')
    assert 0 < pr_snr < 1, f"positive_ratio (snr) should be in (0,1), got {pr_snr}"
    assert 0 < pr_uni < 1, f"positive_ratio (uni) should be in (0,1), got {pr_uni}"
    # SNR and uniform should generally differ
    assert pr_snr != pr_uni, "SNR-weighted and uniform should produce different values"


def test_16_get_bpo_ideal_snr():
    """get_bpo_ideal() defaults to SNR-weighted, and accepts 'uniform' — issue #38."""
    xr = ssd_instance.trimmed_copy().xr
    bpo_snr = xr.get_bpo_ideal()                           # default = 'snr'
    bpo_uni = xr.get_bpo_ideal(weighting='uniform')
    assert 0 < bpo_snr < 1, f"bpo_ideal (snr) should be in (0,1), got {bpo_snr}"
    assert 0 < bpo_uni < 1, f"bpo_ideal (uni) should be in (0,1), got {bpo_uni}"
    assert bpo_snr > 0.5, f"SAMPLE1 bpo_ideal (snr) should be > 0.5, got {bpo_snr}"
    # SNR-weighted bpo_ideal is typically NOT the same as uniform
    assert bpo_snr != bpo_uni, "SNR and uniform bpo_ideal should differ"