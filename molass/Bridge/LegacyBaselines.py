"""
Bridge.LegacyBaselines.py
"""

def make_basecurves_from_sd(sd, baseline_type, debug=False):
    from molass_legacy.QuickAnalysis.ModeledPeaks import get_curve_xy_impl
    
    ret = get_curve_xy_impl(sd, baseline_type=baseline_type, return_details=True, debug=debug)
    details = ret[-1]
    return details.baseline_objects, details.baseline_params
