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

    return details.baseline_objects, details.baseline_params

def make_equivalent_uv_baseparams(sd, details):
    uv_baseparams, xr_baseparams = details.baseline_params
    uv_baseparams = np.zeros(len(uv_baseparams))
    uv_baseparams[0:len(xr_baseparams)] = xr_baseparams
    details.baseline_params[0] = uv_baseparams
    return details
