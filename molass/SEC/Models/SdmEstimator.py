"""
SEC.Models.SdmEstimator.py
"""
import numpy as np
from scipy.optimize import minimize

def estimate_sdm_column_params(decomposition, **kwargs):
    """
    Estimate column parameters from the initial curve and component curves.

    N, T, me, mp, N0, t0, poresize
    """
    debug = kwargs.get('debug', False)

    rgv = np.asarray(decomposition.get_rgs())
    xr_ccurves = decomposition.xr_ccurves

    moment_list = []
    for ccurve in xr_ccurves:
        moment = ccurve.get_moment() 
        mean, std = moment.get_meanstd()
        moment_list.append((mean, std**2))

    me = 1.5
    mp = 1.5

    def objective_function(params):
        N, T, N0, t0, poresize = params
        rhov = rgv/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0

        error = 0.0
        for (mean, var), rho in zip(moment_list, rhov):
            ni = N*(1 - rho)**me
            ti = T*(1 - rho)**mp
            model_mean = t0 + ni*ti
            model_var = 2*ni*ti**2 + model_mean**2/N0
            error += (mean - model_mean)**2 + (var - model_var)**2
        return error
    
    initial_guess = [500, 1.0, 10000, 0, 80.0]
    bounds = [(100, 5000), (1e-3, 5), (500, 50000), (-1000, 1000), (70, 300)]
    result = minimize(objective_function, initial_guess, bounds=bounds)
    if debug:
        print("Rgs:", rgv)
        print("Optimization success:", result.success)
        print("Estimated parameters: N=%g, T=%g, N0=%g, t0=%g, poresize=%g" % tuple(result.x))
        print("Objective function value:", result.fun)
    N, T, N0, t0, poresize = result.x
    return N, T, me, mp, N0, t0, poresize