"""
SEC.Models.SdmEstimator.py
"""
import numpy as np
from scipy.optimize import minimize

def estimate_sdm_column_params(decomposition, **kwargs):
    """
    Estimate column parameters from the initial curve and component curves.

    N, T, me, mp, N0, t0, poresize

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition containing the initial curve and component curves.
    kwargs : dict
        Additional parameters for the estimation process.
        
    Returns
    -------
    (N, T, me, mp, N0, t0, poresize) : tuple
        Estimated parameters for the SDM column.
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

    def objective_function(params, return_moments=False):
        N, T, N0, t0, poresize = params
        rhov = rgv/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0

        error = 0.0
        if return_moments:
            modeled_moments = []
        for (mean, var), rho in zip(moment_list, rhov):
            ni = N*(1 - rho)**me
            ti = T*(1 - rho)**mp
            model_mean = t0 + ni*ti
            model_var = 2*ni*ti**2 + model_mean**2/N0
            error += (mean - model_mean)**2 * (var - model_var)**2      # minimize both mean and variance differences 
            if return_moments:
                modeled_moments.append((model_mean, model_var))
        if return_moments:
            return modeled_moments
        return error
    
    initial_guess = [500, 1.0, 10000, 0, 80.0]
    bounds = [(100, 5000), (1e-3, 5), (500, 50000), (-1000, 1000), (70, 300)]
    result = minimize(objective_function, initial_guess, bounds=bounds)
    if debug:
        import matplotlib.pyplot as plt
        print("Rgs:", rgv)
        print("Optimization success:", result.success)
        print("Estimated parameters: N=%g, T=%g, N0=%g, t0=%g, poresize=%g" % tuple(result.x))
        print("Objective function value:", result.fun)
        x, y = decomposition.xr_icurve.get_xy()
        modeled_moments = objective_function(result.x, return_moments=True)
        fig, ax = plt.subplots()
        ax.plot(x, y, label='Initial Curve')
        for i, ccurve in enumerate(decomposition.xr_ccurves):
            mean, var = moment_list[i]
            std = np.sqrt(var)
            ax.axvline(mean, color='gray', linestyle='--', label=f'Component {i+1} Mean')
            ax.fill_betweenx([0, max(y)], mean - std, mean + std, color='gray', alpha=0.3, label=f'Component {i+1} Std Dev')
            modeled_mean, modeled_var = modeled_moments[i]
            modeled_std = np.sqrt(modeled_var)
            ax.axvline(modeled_mean, color='blue', linestyle='--', label=f'Modeled Component {i+1} Mean')
            ax.fill_betweenx([0, max(y)], modeled_mean - modeled_std, modeled_mean + modeled_std, color='blue', alpha=0.3, label=f'Modeled Component {i+1} Std Dev')
            cx, cy = ccurve.get_xy()
            ax.plot(cx, cy, label=f'Component {i+1}')
        ax.legend()
        plt.show()
    N, T, N0, t0, poresize = result.x
    return N, T, me, mp, N0, t0, poresize