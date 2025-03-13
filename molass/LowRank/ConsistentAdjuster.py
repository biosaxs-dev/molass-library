"""
ConsistentAdjuster.py
"""
import numpy as np
from scipy.optimize import minimize

def _debug_plot(title, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves):
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 4))
    fig.suptitle(title)
    ax1.plot(*uv_icurve.get_xy())
    for uv_ccurve in uv_ccurves:
        ax1.plot(*uv_ccurve.get_xy(), ":")
    ax2.plot(*xr_icurve.get_xy())
    for xr_ccurve in xr_ccurves:
        ax2.plot(*xr_ccurve.get_xy(), ":")
    plt.show()

def adjust_components_consistently(mapping, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs):
    """
    Adjust the component curves consistently.
    """
    from molass.LowRank.ComponentCurve import ComponentCurve
    debug = kwargs.get('debug', False)
    if debug:
        print("adjust_components_consistently entry: mapping=", mapping)
        _debug_plot("adjust_components_consistently entry", xr_icurve, xr_ccurves, uv_icurve, uv_ccurves)

    slope = mapping.slope
    intercept = mapping.intercept
    num_components = len(xr_ccurves)

    xr_x = xr_icurve.x
    x = xr_x * slope + intercept
    spline = uv_icurve.get_spline()
    y = spline(x)

    def adjust_objective(p):
        cy_list = []
        for curve, scale in zip(xr_ccurves, p):
            cy = curve.get_xy()[1] * scale
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        return np.sum((ty - y)**2)

    init_scales = [uv_c.params[0]/xr_c.params[0]  for xr_c, uv_c in zip(xr_ccurves, uv_ccurves)]
    res = minimize(adjust_objective, init_scales, method='Nelder-Mead')

    uv_x = uv_icurve.x
    new_ccurves = []
    for xr_c, scale in zip(xr_ccurves, res.x):
        h, m, s, t = xr_c.params
        ccurve = ComponentCurve(uv_x, [h*scale, m*slope+intercept, s*slope, t*slope])
        new_ccurves.append(ccurve)
    
    if debug:
        _debug_plot("adjust_components_consistently adjusted", xr_icurve, xr_ccurves, uv_icurve, new_ccurves)
    
    return new_ccurves

