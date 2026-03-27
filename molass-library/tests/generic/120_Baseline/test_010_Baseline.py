"""
    test Baseline Correction
"""
import os
import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, repo_root)
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']
from molass.Testing import control_matplotlib_plot, is_interactive

@control_matplotlib_plot
def test_010_OA_Ald_default():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    ssd.plot_compact(baseline=True, debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=is_interactive())
    corrected_ssd.plot_compact(baseline=True, debug=is_interactive())

@control_matplotlib_plot
def test_020_OA_Ald_uvdiff():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    ssd.set_baseline_method(('linear', 'uvdiff'))
    ssd.plot_compact(baseline=True, debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=is_interactive())
    corrected_ssd.plot_compact(baseline=True, debug=is_interactive())

@control_matplotlib_plot
def test_031_OA_Ald_integral():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    ssd.set_baseline_method('integral')
    ssd.plot_compact(baseline=True, debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=is_interactive())
    corrected_ssd.plot_compact(baseline=True, debug=is_interactive())

@control_matplotlib_plot
def test_032_SAMPLE2_integral():
    from molass_data import SAMPLE2
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE2)
    ssd.set_baseline_method('integral')
    ssd.plot_compact(baseline=True, debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy(debug=is_interactive())
    corrected_ssd.plot_compact(baseline=True, debug=is_interactive())

def test_040_endpoint_fraction_differs_from_lpm():
    """get_baseline2d(endpoint_fraction=0.15) must differ from standard LPM.

    Uses a synthetic SsMatrixData-like object with a planted negative dip so
    that the standard LPM anchor is contaminated, then verifies that the
    endpoint-anchored baseline is numerically different and that the standard
    path is unchanged (endpoint_fraction=None produces the original result).
    Also verifies new arg order (M, iv, jv) and E optional.
    """
    import numpy as np
    from molass.DataObjects.SsMatrixData import SsMatrixData

    rng = np.random.default_rng(42)
    n_q, n_frames = 10, 200
    frames = np.arange(n_frames, dtype=float)

    # True linear baseline: slope=0.005, intercept=1.0 per q-row
    true_bl = 0.005 * frames + 1.0
    # Gaussian protein peak + negative dip after it
    peak = 2.0 * np.exp(-0.5 * ((frames - 80) / 8) ** 2)
    neg_dip = -0.6 * np.exp(-0.5 * ((frames - 130) / 6) ** 2)
    signal = true_bl + peak + neg_dip
    M = np.tile(signal, (n_q, 1)) + rng.normal(0, 0.01, (n_q, n_frames))
    q = np.linspace(0.01, 0.3, n_q)

    # Issue #49: M first, then iv, jv
    # Issue #47: E omitted (defaults to None)
    ssd = SsMatrixData(M, q, frames)

    bl_standard = ssd.get_baseline2d(method='linear')
    bl_endpoint = ssd.get_baseline2d(method='linear', endpoint_fraction=0.15)

    # They must differ
    assert not np.allclose(bl_standard, bl_endpoint), \
        "endpoint baseline should differ from standard LPM"

    # Endpoint baseline should be closer to the true linear baseline
    err_standard = np.mean((bl_standard - true_bl) ** 2)
    err_endpoint = np.mean((bl_endpoint - true_bl) ** 2)
    assert err_endpoint < err_standard, \
        f"endpoint MSE ({err_endpoint:.6f}) should be < LPM MSE ({err_standard:.6f})"

    # Calling without endpoint_fraction still gives the original LPM result
    bl_default = ssd.get_baseline2d(method='linear')
    np.testing.assert_array_equal(bl_standard, bl_default)


def test_050_allow_negative_peaks_stored_state():
    """allow_negative_peaks=True must exclude negative-peak frames from LPM, not switch to endpoint anchoring.

    Verifies issue #51 redesign:
    - set_allow_negative_peaks() stores state and negative_peak_mask
    - get_baseline2d() masks negative-peak frames from LPM anchor pool
    - auto-detection (mask=None) uses recognition curve y < 0
    - manual mask (slice) works equivalently
    - copy() propagates both allow_negative_peaks and negative_peak_mask
    - allow_negative_peaks is no longer equivalent to endpoint_fraction=0.15
    """
    import numpy as np
    from molass.DataObjects.SsMatrixData import SsMatrixData

    rng = np.random.default_rng(42)
    n_q, n_frames = 10, 200
    frames = np.arange(n_frames, dtype=float)
    true_bl = 0.005 * frames + 1.0
    peak = 2.0 * np.exp(-0.5 * ((frames - 80) / 8) ** 2)
    # Amplitude -2.5 ensures the recognition curve (M.sum over q) goes negative
    # at the dip region (~frame 130), triggering auto-detection.
    neg_dip = -2.5 * np.exp(-0.5 * ((frames - 130) / 6) ** 2)
    M = np.tile(true_bl + peak + neg_dip, (n_q, 1)) + rng.normal(0, 0.01, (n_q, n_frames))
    q = np.linspace(0.01, 0.3, n_q)

    # --- auto-detect: frames where recognition curve < 0 should be excluded ---
    ssd = SsMatrixData(M, q, frames)
    ssd.set_allow_negative_peaks()
    assert ssd.allow_negative_peaks is True
    assert ssd.negative_peak_mask is None  # None = auto-detect

    bl_auto = ssd.get_baseline2d(method='linear')

    # standard LPM (no flag) should differ — negative frames contaminate the anchor pool
    ssd_std = SsMatrixData(M, q, frames)
    bl_standard = ssd_std.get_baseline2d(method='linear')
    assert not np.allclose(bl_auto, bl_standard), \
        "allow_negative_peaks=True (auto) must differ from unmasked LPM when negative frames exist"

    # --- manual mask: slice covering the negative-peak region ---
    ssd2 = SsMatrixData(M, q, frames)
    ssd2.set_allow_negative_peaks(mask=slice(120, 145))
    bl_manual = ssd2.get_baseline2d(method='linear')

    # manual mask should also differ from standard LPM
    assert not np.allclose(bl_manual, bl_standard), \
        "manual mask must also differ from unmasked LPM"

    # --- copy() must propagate allow_negative_peaks and negative_peak_mask ---
    ssd_copy = ssd.copy()
    assert ssd_copy.allow_negative_peaks is True, "copy() must propagate allow_negative_peaks"
    assert ssd_copy.negative_peak_mask is None, "copy() must propagate negative_peak_mask"
    bl_copy = ssd_copy.get_baseline2d(method='linear')
    np.testing.assert_array_almost_equal(bl_copy, bl_auto,
        err_msg="copied object must produce same masked baseline")

    ssd_copy2 = ssd2.copy()
    assert ssd_copy2.negative_peak_mask == slice(120, 145), \
        "copy() must propagate explicit slice mask"

    # --- allow_negative_peaks is NO LONGER equivalent to endpoint_fraction=0.15 ---
    bl_endpoint = ssd_std.get_baseline2d(method='linear', endpoint_fraction=0.15)
    assert not np.allclose(bl_auto, bl_endpoint), \
        "masked LPM must not equal endpoint-anchored baseline (different algorithms)"


def test_052_slice_mask_uses_frame_numbers():
    """Issue #52: slice mask must interpret start/stop as frame numbers, not array indices.

    When jv starts at a non-zero offset (e.g. frames 400-600), slice(450, 500)
    should exclude frames 450-500, not array indices 450-500 (which would be
    out of bounds and silently do nothing).
    """
    import numpy as np
    from molass.DataObjects.SsMatrixData import SsMatrixData

    rng = np.random.default_rng(52)
    n_q, n_frames = 10, 200
    # Frames start at 400, not 0 — just like trimmed real data
    frames = np.arange(400, 400 + n_frames, dtype=float)
    true_bl = 0.005 * frames + 1.0
    peak = 2.0 * np.exp(-0.5 * ((frames - 460) / 8) ** 2)
    # Strong negative dip at frames ~510-530
    neg_dip = -5.0 * np.exp(-0.5 * ((frames - 520) / 6) ** 2)
    M = np.tile(true_bl + peak + neg_dip, (n_q, 1)) + rng.normal(0, 0.01, (n_q, n_frames))
    q = np.linspace(0.01, 0.3, n_q)

    ssd = SsMatrixData(M, q, frames)

    # Standard LPM (contaminated by negative dip)
    bl_standard = ssd.get_baseline2d(method='linear')

    # Manual mask with frame numbers — this is the natural usage
    ssd.set_allow_negative_peaks(mask=slice(510, 535))
    bl_masked = ssd.get_baseline2d(method='linear')
    ssd.set_allow_negative_peaks(False)

    # The manual mask must actually do something (not be a silent no-op)
    assert not np.allclose(bl_masked, bl_standard), \
        "slice(510, 535) with frame-number jv starting at 400 must NOT be a no-op"

    # Verify the correct frames were excluded: the dip region should be masked
    # so the masked baseline should be closer to the true linear baseline
    err_standard = np.mean((bl_standard - true_bl) ** 2)
    err_masked = np.mean((bl_masked - true_bl) ** 2)
    assert err_masked < err_standard, \
        f"masked MSE ({err_masked:.6f}) should be < standard MSE ({err_standard:.6f})"


def test_053_ssd_set_allow_negative_peaks_delegation():
    """Issue #53: SecSaxsData.set_allow_negative_peaks() must delegate to xr (and uv)."""
    import numpy as np
    from molass.DataObjects.XrData import XrData
    from molass.DataObjects.UvData import UvData
    from molass.DataObjects.SecSaxsData import SecSaxsData

    rng = np.random.default_rng(53)
    n_q, n_wl, n_frames = 10, 5, 200
    frames = np.arange(400, 400 + n_frames, dtype=float)
    q = np.linspace(0.01, 0.3, n_q)
    wl = np.linspace(250, 300, n_wl)
    M_xr = rng.normal(1.0, 0.01, (n_q, n_frames))
    M_uv = rng.normal(0.5, 0.01, (n_wl, n_frames))

    xr = XrData(M_xr, q, frames)
    uv = UvData(M_uv, wl, frames)
    ssd = SecSaxsData(object_list=[xr, uv])

    # Must not raise AttributeError
    ssd.set_allow_negative_peaks()
    assert ssd.xr.allow_negative_peaks is True
    assert ssd.uv.allow_negative_peaks is True

    # Reset
    ssd.set_allow_negative_peaks(False)
    assert ssd.xr.allow_negative_peaks is False
    assert ssd.uv.allow_negative_peaks is False

    # With manual mask
    ssd.set_allow_negative_peaks(mask=slice(450, 500))
    assert ssd.xr.negative_peak_mask == slice(450, 500)
    assert ssd.uv.negative_peak_mask == slice(450, 500)


if __name__ == "__main__":
    # test_010_OA_Ald_default()
    # test_020_OA_Ald_uvdiff()
    # test_031_OA_Ald_integral()
    test_032_SAMPLE2_integral()
    # plt.show()