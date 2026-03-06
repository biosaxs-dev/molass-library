"""
SEC.Models.SdmOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf, DEFUALT_TIMESCALE

def optimize_sdm_xr_decomposition(decomposition, env_params, model_params=None, **kwargs):
    """ Optimize the SDM decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    env_params : tuple
        The environmental parameters (N, T, me, mp, N0, t0, poresize).
    model_params : dict, optional
        The parameters for the SDM model.
    kwargs : dict
        Additional parameters for the optimization process.

    Returns
    -------
    new_xr_ccurves : list of SdmComponentCurve
        The optimized SDM component curves.
    """
    # N, T, N0, t0, poresize
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.SdmComponentCurve
        reload(molass.SEC.Models.SdmComponentCurve)
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve

    num_components = decomposition.num_components
    xr_icurve = decomposition.xr_icurve
    x, y = xr_icurve.get_xy()
    N, T, me, mp, N0, t0, poresize = env_params
    rgv = np.asarray(decomposition.get_rgs())

    if model_params is None:
        timescale = DEFUALT_TIMESCALE
    else:
        timescale = model_params.get('timescale', DEFUALT_TIMESCALE)

    def estimate_initial_scales():
        scales = []
        for rg in rgv:
            column = SdmColumn([N, T, me, mp, t0, t0, N0, poresize, timescale])
            ccurve = SdmComponentCurve(x, column, rg, scale=1.0)
            cy = ccurve.get_y()
            k = np.argmax(cy)
            scale = y[k]/cy[k]
            scales.append(scale)
        return scales

    def objective_function(params, return_cy_list=False, plot=False):
        N_, T_, x0_, tI_, N0_ = params[0:5]
        rgv_ = params[5:5+num_components]
        rg_diff = np.diff(rgv_)
        non_ordered = np.where(rg_diff > 0)[0]
        order_penalty = np.sum(rg_diff[non_ordered]**2) * 1e3  # penalty for non-ordered rgv
        rhov = rgv_/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0
        scales_ = params[5+num_components:5+2*num_components]
        cy_list = []
        x_ = x - tI_
        t0 = x0_ - tI_
        for rho, scale in zip(rhov, scales_):
            ni = N_*(1 - rho)**me
            ti = T_*(1 - rho)**mp
            cy = scale * dispersive_monopore_pdf(x_, ni, ti, N0_, t0, timescale=timescale)
            cy_list.append(cy)
        if return_cy_list:
            return cy_list
        ty = np.sum(cy_list, axis=0)
        if plot:
            import matplotlib.pyplot as plt
            plt.figure()
            plt.plot(x, y, label='Data')
            plt.plot(x, ty, label='Model')
            for i, cy in enumerate(cy_list):
                plt.plot(x, cy, label='Component %d' % (i+1))
            plt.legend()
            plt.show()
        error = np.sum((y - ty)**2) + order_penalty
        return error

    initial_guess = [N, T, t0, t0, N0]
    initial_guess += list(rgv)

    initial_scales = estimate_initial_scales()
    initial_guess += initial_scales
    # objective_function(initial_guess, plot=True)
    if False:
        cy_list = objective_function(initial_guess, return_cy_list=True)
        for i, cy in enumerate(cy_list):
            k = np.argmax(cy)
            scale = initial_scales[i]*y[k]/cy[k]
            initial_guess[5+num_components + i] = scale

    # Set bounds for the parameters
    bounds = [(100, 5000), (1e-3, 5), (t0 - 1000, t0 + 1000), (t0 - 1000, t0 + 1000), (500, 50000)]
    bounds += [(rg*0.5, rg*1.5) for rg in rgv]
    upper_scale = xr_icurve.get_max_y() * 1000      # upper bounds for scales seem be large enough
    bounds += [(1e-3, upper_scale) for _ in range(num_components)]
    if model_params is None:
        method = None
    else:
        method = model_params.get('method', 'Nelder-Mead')
    result = minimize(objective_function, initial_guess, bounds=bounds, method=method)

    if debug:
        print("Optimization success:", result.success)
        print("Optimized parameters: N=%g, T=%g, x0=%g, tI=%g, N0=%g" % tuple(result.x[0:5]))
        print("Rgs:", result.x[5:5+num_components])
        print("Objective function value:", result.fun)

    N_, T_, x0_, tI_, N0_ = result.x[0:5]
    rgv_ = result.x[5:5+num_components]
    scales_ = result.x[5+num_components:5+2*num_components]
    column = SdmColumn([N_, T_, me, mp, x0_, tI_, N0_, poresize, DEFUALT_TIMESCALE])
    print("initial_scales:", initial_scales)
    print("optimized scales_:", scales_)
    new_xr_ccurves = []
    for rg, scale in zip(rgv_, scales_):
        ccurve = SdmComponentCurve(x, column, rg, scale)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves

def optimize_sdm_uv_decomposition(decomposition, xr_ccurves, **kwargs):
    """ Optimize the SDM UV decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    xr_ccurves : list of SdmComponentCurve
        The SDM component curves from the XR decomposition.
    kwargs : dict
        Additional parameters for the optimization process.
        
    Returns
    -------
    new_uv_ccurves : list of UvComponentCurve
        The optimized UV component curves.
    """
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

def adjust_rg_and_poresize(sdm_decomposition, rgcurve=None):
    """ Adjust rg and poresize in the decomposition based on the optimized component curves.
    """
    from .SdmComponentCurve import SdmColumn
    rgs = np.array(sdm_decomposition.get_rgs())     # get SAXS rgs
    xr_ccurves = sdm_decomposition.xr_ccurves
    column = xr_ccurves[0].column
    column_params = column.get_params()
    poresize = column_params[-2]
    rhov = []
    for i, ccurve in enumerate(xr_ccurves):
        rg = ccurve.rg
        rho = min(1, rg/poresize)
        rhov.append(rho)
    rhov = np.array(rhov)

    def posize_adjustment_error(poresize_):
        model_rgv = rhov * poresize_
        error = np.sum((model_rgv - rgs))**2
        return error
    
    result = minimize(posize_adjustment_error, poresize, bounds=[(poresize*0.5, poresize*1.5)])
    new_poresize = result.x[0]
    print("Adjusted poresize from %g to %g" % (poresize, new_poresize))

    new_column = SdmColumn(list(column_params[0:-2]) + [new_poresize, column_params[-1]])
    for i, ccurve in enumerate(xr_ccurves):
        ccurve.column = new_column
        ccurve.rg = rhov[i] * new_poresize
        



 