"""
SEC.Models.UvOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize

def optimize_uv_decomposition(decomposition, xr_ccurves, **kwargs):
    debug = kwargs.get('debug', False)
    from molass.Mapping.Mapping import Mapping
    if debug:
        from importlib import reload
        import molass.SEC.Models.UvComponentCurve
        reload(molass.SEC.Models.UvComponentCurve)
    from .UvComponentCurve import UvComponentCurve

    num_components = decomposition.num_components
    x, y = decomposition.uv_icurve.get_xy()

    def objective_function(params):
        a_, b_ = params[0:2]
        mapping = Mapping(a_, b_)
        scales_ = params[2:2+num_components]
        cy_list = []
        for xr_ccurve, scale in zip(xr_ccurves, scales_):
            uv_ccurve = UvComponentCurve(x, mapping, xr_ccurve, scale)
            cy = uv_ccurve.get_y()
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        error = np.sum((y - ty)**2)
        return error

    mapping = decomposition.mapping
    a, b = mapping.slope, mapping.intercept

    initial_guess = [a, b] + [1.0]*num_components
    dx = (x[-1] - x[0])*0.1
    bounds = [(a*0.8, a*1.2), (b-dx, b+dx)] + [(1e-3, 10.0) for _ in range(num_components)]
    result = minimize(objective_function, initial_guess, bounds=bounds)

    new_mapping = Mapping(*result.x[0:2])
    new_uv_ccurves = []
    for xr_ccurve, scale in zip(xr_ccurves, result.x[2:]):
        ccurve = UvComponentCurve(x, new_mapping, xr_ccurve, scale)
        new_uv_ccurves.append(ccurve)
    return new_uv_ccurves
