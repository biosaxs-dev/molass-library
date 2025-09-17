"""
    Baseline.UvBaseline.py
"""
import numpy as np
from scipy.optimize import minimize
from molass.DataObjects.Curve import Curve
from molass.Baseline.UvDiffEffect import create_diff_spline

class UvBaseline(Curve):
    def __init__(self, ssd, params=None):
        from molass_legacy.Baseline.UvBaseSpline import compute_baseline_impl
        from molass_legacy.Baseline.Constants import SLOPE_SCALE
        icurve = ssd.uv.get_icurve()
        diff_spline = create_diff_spline(icurve)
        x = icurve.x
        temp_params = params.copy()
        temp_params[4:6] /= SLOPE_SCALE
        y = compute_baseline_impl(x, temp_params[0:7], diff_spline)
        super().__init__(x, y)
        self.params = params

def estimate_uvbaseline_params(curve1, curve2, pickat=None, plot_info=None, counter=None, return_also_baseline=False, debug=False):
    if debug:
        from importlib import reload
        import molass.FlowChange.FlowChange
        reload(molass.FlowChange.FlowChange)
        import molass.Baseline.UvDiffEffect
        reload(molass.Baseline.UvDiffEffect)
        import molass.Baseline.SimpleBaseline
        reload(molass.Baseline.SimpleBaseline)
    from molass.FlowChange.FlowChange import flowchange_exclude_slice
    from molass.Baseline.UvDiffEffect import estimate_uvdiffeffect_params, compute_dfef_curve
    from molass.Baseline.SimpleBaseline import estimate_baseline_params

    # 	            L	        x0	    k	        b	        s1	    s2	    diff_ratio
    # uv_baseline	0.00711615	135.851	0.860483	-0.004567	11.3408	12.131	0.6397

    fc_slice = flowchange_exclude_slice(curve1, curve2, debug=debug, counter=counter)[0]

    diff_spline = create_diff_spline(curve1)
    dfef_params, dy, baseline = estimate_uvdiffeffect_params(curve1, curve2, fc_slice, diff_spline, pickat=pickat, debug=debug, plot_info=plot_info)
    dfef_curve = compute_dfef_curve(curve1.x, dfef_params)
    curve1_ = curve1 - dfef_curve
    
    base_params = estimate_baseline_params(curve1_, debug=debug)
    uvbaseline_params = np.concatenate([dfef_params, base_params])
    if return_also_baseline:
        return uvbaseline_params, dy, baseline
    else:
        return uvbaseline_params

def inspect_uv_baseline(uv_data, pickat=400, smooth=False, return_also_plotresult=False, title=None, debug=False):
    """
    Estimate UV baseline parameters and plot the result.
    """
    import matplotlib.pyplot as plt
    c1 = uv_data.get_icurve()
    c2 = uv_data.get_icurve(pickat=pickat)
    if smooth:
        c1_ = c1.smooth_copy()
        c2_ = c2.smooth_copy()
    else:
        c1_ = c1
        c2_ = c2
    fig, ax = plt.subplots()
    if title is not None:
        fig.suptitle(title) 
    params = estimate_uvbaseline_params(c1_, c2_, pickat=pickat, plot_info=(fig, ax), debug=debug)
    if return_also_plotresult:
        from molass.PlotUtils.PlotResult import PlotResult
        return params, PlotResult(fig, (ax,))
    else:
        return params