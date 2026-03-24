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
    """allow_negative_peaks=True stored on object must give same result as endpoint_fraction=0.15.

    Verifies issue #50: set_allow_negative_peaks() stores state, get_baseline2d()
    honours it, and copy() propagates it.
    """
    import numpy as np
    from molass.DataObjects.SsMatrixData import SsMatrixData

    rng = np.random.default_rng(42)
    n_q, n_frames = 10, 200
    frames = np.arange(n_frames, dtype=float)
    true_bl = 0.005 * frames + 1.0
    peak = 2.0 * np.exp(-0.5 * ((frames - 80) / 8) ** 2)
    neg_dip = -0.6 * np.exp(-0.5 * ((frames - 130) / 6) ** 2)
    M = np.tile(true_bl + peak + neg_dip, (n_q, 1)) + rng.normal(0, 0.01, (n_q, n_frames))
    q = np.linspace(0.01, 0.3, n_q)

    # Explicit endpoint_fraction kwarg
    ssd = SsMatrixData(M, q, frames)
    bl_explicit = ssd.get_baseline2d(method='linear', endpoint_fraction=0.15)

    # Via set_allow_negative_peaks() — should give identical result
    ssd.set_allow_negative_peaks()
    assert ssd.allow_negative_peaks is True
    bl_via_flag = ssd.get_baseline2d(method='linear')
    np.testing.assert_array_almost_equal(bl_via_flag, bl_explicit,
        err_msg="allow_negative_peaks=True must produce same baseline as endpoint_fraction=0.15")

    # copy() must propagate the flag
    ssd_copy = ssd.copy()
    assert ssd_copy.allow_negative_peaks is True, "copy() must propagate allow_negative_peaks"
    bl_copy = ssd_copy.get_baseline2d(method='linear')
    np.testing.assert_array_almost_equal(bl_copy, bl_explicit,
        err_msg="copied object must produce same endpoint baseline")

    # Default (flag=False) must NOT use endpoint method
    ssd_default = SsMatrixData(M, q, frames)
    bl_default = ssd_default.get_baseline2d(method='linear')
    assert not np.allclose(bl_default, bl_explicit), \
        "default (allow_negative_peaks=False) must not equal endpoint baseline"


if __name__ == "__main__":
    # test_010_OA_Ald_default()
    # test_020_OA_Ald_uvdiff()
    # test_031_OA_Ald_integral()
    test_032_SAMPLE2_integral()
    # plt.show()