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
        fig, ax = plt.subplots(figsize=(8,5))
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


def estimate_sdm_lognormal_column_params(decomposition, **kwargs):
    """
    Estimate column parameters for SDM with lognormal pore distribution.

    Runs the mono-pore estimator first, then converts poresize to
    lognormal parameters (mu, sigma).

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition containing the initial curve and component curves.
    kwargs : dict
        Additional parameters for the estimation process.

    Returns
    -------
    (N, T, me, mp, N0, t0, mu, sigma) : tuple
        Estimated parameters for the SDM column with lognormal pore distribution.
    """
    N, T, me, mp, N0, t0, poresize = estimate_sdm_column_params(decomposition, **kwargs)
    mu = np.log(poresize)
    sigma = 0.3  # initial breadth for optimizer to refine
    return N, T, me, mp, N0, t0, mu, sigma


def estimate_sdm_lognormal_from_monopore(mono_ccurves, xr_icurve, **kwargs):
    """
    Estimate lognormal column parameters from converged mono-pore SDM results.

    Converts the mono-pore column parameters to lognormal initial guess by:
    1. Extracting converged (N, T, x0, tI, N0, k) from the mono-pore result
    2. Deriving effective poresize from Rg (not the estimator's stored value)
    3. Setting mu=ln(poresize), sigma=0.3
    4. Shifting x0/tI to align the lognormal PDF peak with the data peak

    Parameters
    ----------
    mono_ccurves : list of SdmComponentCurve
        Converged mono-pore component curves.
    xr_icurve : Curve
        The XR integrated elution curve (data).
    kwargs : dict
        Additional parameters (debug, etc.).

    Returns
    -------
    (N, T, me, mp, N0, t0_adj, mu, sigma) : tuple
        Estimated parameters for the lognormal SDM optimizer.
    """
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve

    debug = kwargs.get('debug', False)
    column = mono_ccurves[0].column
    N, T, me, mp, x0, tI, N0, poresize_stored, timescale, k = column.get_params()

    # The estimator's poresize is not optimized by the mono-pore optimizer.
    # Derive an effective poresize from the optimized Rg values instead.
    # In SEC, K_SEC ~ 0.5 corresponds to poresize ~ 2.5 * Rg.
    rg_max = max(cc.rg for cc in mono_ccurves)
    effective_poresize = 2.5 * rg_max
    mu = np.log(effective_poresize)
    sigma = 0.3

    # Create a test lognormal PDF with the dominant component to find peak position
    x_data, y_data = xr_icurve.get_xy()
    rg_dominant = mono_ccurves[0].rg
    col_test = SdmColumn([N, T, me, mp, x0, tI, N0, mu, sigma, k],
                         pore_dist='lognormal', rt_dist=column.rt_dist)
    cc_test = SdmComponentCurve(x_data, col_test, rg_dominant, scale=1.0)
    cy_test = cc_test.get_y()
    pdf_peak = x_data[np.argmax(cy_test)]
    data_peak = x_data[np.argmax(y_data)]
    shift = data_peak - pdf_peak

    # t0 for the optimizer (sets both x0 and tI to this value initially)
    t0_adj = x0 + shift

    if debug:
        print(f"Lognormal from mono-pore: Rg_max={rg_max:.1f}, effective_poresize={effective_poresize:.1f}")
        print(f"  stored poresize={poresize_stored:.1f} (not used), mu={mu:.4f}")
        print(f"  PDF peak={pdf_peak:.0f}, data peak={data_peak:.0f}, shift={shift:.0f}")
        print(f"  x0: {x0:.1f} → {x0 + shift:.1f}, t0_adj={t0_adj:.1f}")

    return N, T, me, mp, N0, t0_adj, mu, sigma