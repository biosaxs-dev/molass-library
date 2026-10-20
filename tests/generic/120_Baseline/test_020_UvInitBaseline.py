"""
    test the initial UV baseline parameters handed to the rigorous optimizer (issue #311)
"""
import os
import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, repo_root)
import numpy as np
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used

def test_010_uv_slopes_keep_scaled_convention():
    from molass_data import SAMPLE1
    from molass.DataObjects import SecSaxsData as SSD
    from molass.Bridge.SdProxy import SdProxy
    from molass.Bridge.LegacyBaselines import make_basecurves_from_sd
    from molass_legacy.QuickAnalysis.ModeledPeaks import get_curve_xy_impl
    from molass_legacy.Baseline.Constants import SLOPE_SCALE

    trimmed = SSD(SAMPLE1).trimmed_copy()
    sd = SdProxy(trimmed)
    basecurves, baseparams = make_basecurves_from_sd(sd, 1)
    uv_baseparams = baseparams[0]

    # get_curve_xy_impl stores the slopes already divided by SLOPE_SCALE
    details = get_curve_xy_impl(sd, baseline_type=1, return_details=True)[-1]
    raw = details.baseline_params[0]
    assert np.allclose(uv_baseparams[0:4], raw[0:4], rtol=1e-3, atol=1e-6)
    assert np.allclose(uv_baseparams[4:6], raw[4:6]*SLOPE_SCALE, rtol=1e-3, atol=1e-9)

    # the baseline the optimizer computes must follow the sigmoid with the real slopes
    from molass_legacy.Baseline.UvBaseSpline import compute_baseline_impl
    uv_base_curve = basecurves[0]
    x = details.uv_curve.x
    expected = compute_baseline_impl(x, raw[0:7], uv_base_curve.diff_spline)
    assert np.allclose(uv_base_curve(x, uv_baseparams, None), expected, atol=1e-6)
