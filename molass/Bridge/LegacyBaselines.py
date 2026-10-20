"""
Bridge.LegacyBaselines.py
"""
import numpy as np

def make_basecurves_from_sd(sd, baseline_type, xr_only=False, debug=False):
    from molass_legacy.QuickAnalysis.ModeledPeaks import get_curve_xy_impl        
    ret = get_curve_xy_impl(sd, baseline_type=baseline_type, return_details=True, debug=debug)
    details = ret[-1]

    if xr_only:
        details = make_equivalent_uv_baseparams(sd, details)
    else:
        details = restore_uv_slope_scale(details)

    return details.baseline_objects, details.baseline_params

def restore_uv_slope_scale(details):
    """get_curve_xy_impl divides the UV sigmoid slopes (params[4:6]) by SLOPE_SCALE,
    but UvBaseSpline.__call__ divides them again, which flattens the initial UV
    baseline. Restore the stored (scaled) convention expected by the optimizer.
    """
    from molass_legacy.Baseline.Constants import SLOPE_SCALE
    uv_baseparams = np.array(details.baseline_params[0], dtype=float)
    uv_baseparams[4:6] *= SLOPE_SCALE
    details.baseline_params[0] = uv_baseparams
    return details

def make_equivalent_uv_baseparams(sd, details):
    uv_baseparams, xr_baseparams = details.baseline_params
    uv_baseparams = np.zeros(len(uv_baseparams))
    uv_baseparams[0:len(xr_baseparams)] = xr_baseparams
    details.baseline_params[0] = uv_baseparams
    return details
