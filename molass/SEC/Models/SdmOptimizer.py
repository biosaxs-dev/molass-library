"""
SEC.Models.SdmOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf, DEFUALT_TIMESCALE

def optimize_sdm_xr_decomposition(decomposition, env_params, **kwargs):
    # N, T, N0, t0, poresize
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.SdmComponentCurve
        reload(molass.SEC.Models.SdmComponentCurve)
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve

    num_components = decomposition.num_components
    x, y = decomposition.xr_icurve.get_xy()
    N, T, me, mp, N0, t0, poresize = env_params
    rgv = np.asarray(decomposition.get_rgs())

    def objective_function(params):
        N_, T_, x0_, tI_, N0_ = params[0:5]
        rgv_ = params[5:5+num_components]
        rhov = rgv/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0
        scales_ = params[5+num_components:5+2*num_components]
        cy_list = []
        for rho, scale in zip(rhov, scales_):
            ni = N_*(1 - rho)**me
            ti = T_*(1 - rho)**mp
            cy = scale * dispersive_monopore_pdf(x - tI_, ni, ti, N0_, x0_ - tI_, timescale=DEFUALT_TIMESCALE)
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        error = np.sum((y - ty)**2)
        return error

    initial_guess = [N, T, t0, t0, N0]
    initial_guess += list(rgv)
    initial_guess += [1.0]*num_components
    bounds = [(100, 5000), (1e-3, 5), (t0 - 1000, t0 + 1000), (t0 - 1000, t0 + 1000), (500, 50000)]
    bounds += [(rg*0.5, rg*1.5) for rg in rgv]
    bounds += [(1e-3, 10.0) for _ in range(num_components)]
    result = minimize(objective_function, initial_guess, bounds=bounds)

    if debug:
        print("Optimization success:", result.success)
        print("Optimized parameters: N=%g, T=%g, x0=%g, tI=%g, N0=%g" % tuple(result.x[0:5]))
        print("Rgs:", result.x[5:5+num_components])
        print("Objective function value:", result.fun)

    N_, T_, x0_, tI_, N0_ = result.x[0:5]
    rgv_ = result.x[5:5+num_components]
    scales_ = result.x[5+num_components:5+2*num_components]
    column = SdmColumn([N_, T_, me, mp, x0_, tI_, N0_, poresize, DEFUALT_TIMESCALE])
    new_xr_ccurves = []
    for rg, scale in zip(rgv_, scales_):
        ccurve = SdmComponentCurve(x, column, rg, scale)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves

def optimize_sdm_uv_decomposition(decomposition, xr_ccurves, **kwargs):
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
