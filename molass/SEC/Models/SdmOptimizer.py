"""
SEC.Models.SdmOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf, DEFUALT_TIMESCALE

def optimize_sdm_decomposition_impl(decomposition, env_params, **kwargs):
    # N, T, N0, t0, poresize
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.SdmComponentCurve
        reload(molass.SEC.Models.SdmComponentCurve)
    from .SdmComponentCurve import SdmComponentCurve

    me = 1.5
    mp = 1.5

    def compute_curves(x, N, T, x0, tI, N0, rhov, timescale=DEFUALT_TIMESCALE):
        # modified from molass_legacy.Models.Stochastic.DispersivePdf
        cy_list = []
        for rho in rhov:
            ni = N*(1 - rho)**me
            ti = T*(1 - rho)**mp
            cy = dispersive_monopore_pdf(x - tI, ni, ti, N0, x0 - tI, timescale=timescale)
            cy_list.append(cy)
        return cy_list

    num_components = decomposition.num_components
    x, y = decomposition.xr_icurve.get_xy()
    N, T, N0, t0, poresize = env_params
    rgv = np.asarray(decomposition.get_rgs())

    def objective_function(params):
        N_, T_, x0_, tI_, N0_ = params[0:5]
        rgv_ = params[5:5+num_components]
        rhov = rgv/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0
        cy_list = compute_curves(x, N_, T_, x0_, tI_, N0_, rhov)
        ty = np.sum(cy_list, axis=0)
        error = np.sum((y - ty)**2)
        return error

    initial_guess = [N, T, t0, t0, N0]
    initial_guess += list(rgv)
    bounds = [(100, 5000), (1e-3, 5), (t0 - 1000, t0 + 1000), (t0 - 1000, t0 + 1000), (500, 50000)]
    bounds += [(rg*0.5, rg*1.5) for rg in rgv]
    result = minimize(objective_function, initial_guess, bounds=bounds)

    if debug:
        print("Optimization success:", result.success)
        print("Optimized parameters: N=%g, T=%g, x0=%g, tI=%g, N0=%g" % tuple(result.x[0:5]))
        print("Rgs:", result.x[5:5+num_components])
        print("Objective function value:", result.fun)

    return decomposition
