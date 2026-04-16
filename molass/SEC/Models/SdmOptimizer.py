"""
SEC.Models.SdmOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize
from molass.SEC.Models.SdmMonoPore import (
    sdm_monopore_pdf,
    sdm_monopore_gamma_pdf,
    DEFAULT_TIMESCALE,
)

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
        timescale = DEFAULT_TIMESCALE
        k_init = 2.0
        pore_dist = 'mono'
        rt_dist = 'gamma'
    else:
        timescale = model_params.get('timescale', DEFAULT_TIMESCALE)
        k_init = model_params.get('k', 2.0)
        pore_dist = model_params.get('pore_dist', 'mono')
        rt_dist = model_params.get('rt_dist', 'gamma')

    if rt_dist == 'exponential':
        k_init = 1.0   # not optimized for exponential
        _pdf_func = sdm_monopore_pdf
    else:
        _pdf_func = sdm_monopore_gamma_pdf

    def estimate_initial_scales():
        scales = []
        for rg in rgv:
            column = SdmColumn([N, T, me, mp, t0, t0, N0, poresize, timescale, k_init],
                               pore_dist=pore_dist, rt_dist=rt_dist)
            ccurve = SdmComponentCurve(x, column, rg, scale=1.0)
            cy = ccurve.get_y()
            idx = np.argmax(cy)
            scale = y[idx]/cy[idx] if cy[idx] > 0 else 1.0
            scales.append(scale)
        return scales

    def objective_function(params, return_cy_list=False, plot=False):
        N_, T_, x0_, tI_, N0_, k_ = params[0:6]
        rgv_ = params[6:6+num_components]
        rg_diff = np.diff(rgv_)
        non_ordered = np.where(rg_diff > 0)[0]
        order_penalty = np.sum(rg_diff[non_ordered]**2) * 1e3  # penalty for non-ordered rgv
        rhov = rgv_/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0
        scales_ = params[6+num_components:6+2*num_components]
        cy_list = []
        x_ = x - tI_
        t0 = x0_ - tI_
        for rho, scale in zip(rhov, scales_):
            ni = N_*(1 - rho)**me
            ti = T_*(1 - rho)**mp
            if rt_dist == 'exponential':
                cy = scale * _pdf_func(x_, ni, ti, N0_, t0, timescale=timescale)
            else:
                theta = ti / k_  # Gamma scale: mean = k*theta = ti
                cy = scale * _pdf_func(x_, ni, k_, theta, N0_, t0, timescale=timescale)
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

    initial_guess = [N, T, t0, t0, N0, k_init]
    initial_guess += list(rgv)

    initial_scales = estimate_initial_scales()
    initial_guess += initial_scales
    # objective_function(initial_guess, plot=True)
    if False:
        cy_list = objective_function(initial_guess, return_cy_list=True)
        for i, cy in enumerate(cy_list):
            idx = np.argmax(cy)
            scale = initial_scales[i]*y[idx]/cy[idx] if cy[idx] > 0 else initial_scales[i]
            initial_guess[6+num_components + i] = scale

    # Set bounds for the parameters: N, T, x0, tI, N0, k
    bounds = [(100, 5000), (1e-3, 5), (t0 - 1000, t0 + 1000), (t0 - 1000, t0 + 1000), (500, 50000)]
    if rt_dist == 'exponential':
        bounds += [(0.999, 1.001)]   # k fixed at 1.0
    else:
        bounds += [(0.5, 10.0)]      # k free for gamma
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
        print("Optimized parameters: N=%g, T=%g, x0=%g, tI=%g, N0=%g, k=%g" % tuple(result.x[0:6]))
        print("Rgs:", result.x[6:6+num_components])
        print("Objective function value:", result.fun)

    N_, T_, x0_, tI_, N0_, k_ = result.x[0:6]
    rgv_ = result.x[6:6+num_components]
    scales_ = result.x[6+num_components:6+2*num_components]
    column = SdmColumn([N_, T_, me, mp, x0_, tI_, N0_, poresize, timescale, k_],
                       pore_dist=pore_dist, rt_dist=rt_dist)
    print("initial_scales:", initial_scales)
    print("optimized scales_:", scales_)
    print("optimized k:", k_)
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


def optimize_sdm_lognormal_xr_decomposition(decomposition, env_params, model_params=None, **kwargs):
    """Optimize XR decomposition with SDM lognormal pore distribution.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    env_params : tuple
        The environmental parameters ``(N, T, me, mp, N0, t0, mu, sigma)``.
    model_params : dict, optional
        The parameters for the SDM model.
    kwargs : dict
        Additional parameters for the optimization process.

    Returns
    -------
    new_xr_ccurves : list of SdmComponentCurve
        The optimized SDM component curves with lognormal pore distribution.
    """
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.SdmComponentCurve
        reload(molass.SEC.Models.SdmComponentCurve)
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve
    from molass.SEC.Models.LognormalPore import sdm_lognormal_pore_gamma_pdf_fast

    num_components = decomposition.num_components
    xr_icurve = decomposition.xr_icurve
    x, y = xr_icurve.get_xy()
    N, T, me, mp, N0, t0, mu_init, sigma_init = env_params
    rgv = np.asarray(decomposition.get_rgs())

    if model_params is None:
        k_init = 2.0
        rt_dist = 'gamma'
    else:
        k_init = model_params.get('k', 2.0)
        rt_dist = model_params.get('rt_dist', 'gamma')

    if rt_dist == 'exponential':
        k_init = 1.0

    # Estimate initial scales
    scales_init = []
    for rg in rgv:
        column = SdmColumn([N, T, me, mp, t0, t0, N0, mu_init, sigma_init, k_init],
                           pore_dist='lognormal', rt_dist=rt_dist)
        ccurve = SdmComponentCurve(x, column, rg, scale=1.0)
        cy = ccurve.get_y()
        idx = np.argmax(cy)
        scale = y[idx] / cy[idx] if cy[idx] > 0 else 1.0
        scales_init.append(scale)

    def objective_function(params):
        N_, T_, x0_, tI_, N0_, k_, mu_, sigma_ = params[0:8]
        rgv_ = params[8:8 + num_components]
        scales_ = params[8 + num_components:8 + 2 * num_components]

        if sigma_ < 0.01 or sigma_ > 2.0:
            return 1e20
        if mu_ < 1.0 or mu_ > 8.0:
            return 1e20

        # Rg ordering penalty (Rg should be descending)
        rg_diff = np.diff(rgv_)
        non_ordered = np.where(rg_diff > 0)[0]
        order_penalty = np.sum(rg_diff[non_ordered] ** 2) * 1e3

        x_ = x - tI_
        t0_ = x0_ - tI_
        cy_list = []
        for rg_, scale_ in zip(rgv_, scales_):
            cy = scale_ * sdm_lognormal_pore_gamma_pdf_fast(
                x_, 1.0, N_, T_, k_, me, mp, mu_, sigma_, rg_, N0_, t0_
            )
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        error = np.sum((y - ty) ** 2) + order_penalty
        _eval_count[0] += 1
        n = _eval_count[0]
        if debug and n % 50 == 0:
            print(f"  lognormal opt: {n} evals, error={error:.4g}", flush=True)
        return error

    _eval_count = [0]

    # Initial guess: [N, T, x0, tI, N0, k, mu, sigma, ...Rg, ...scale]
    initial_guess = [N, T, t0, t0, N0, k_init, mu_init, sigma_init]
    initial_guess += list(rgv)
    initial_guess += scales_init

    # Bounds
    bounds = [
        (100, 5000),              # N
        (1e-3, 5),                # T
        (t0 - 1000, t0 + 1000),  # x0
        (t0 - 1000, t0 + 1000),  # tI
        (500, 50000),             # N0
    ]
    if rt_dist == 'exponential':
        bounds += [(0.999, 1.001)]  # k fixed at 1.0
    else:
        bounds += [(0.5, 10.0)]     # k free for gamma
    bounds += [(2.0, 8.0)]          # mu
    bounds += [(0.01, 2.0)]         # sigma
    bounds += [(rg * 0.5, rg * 1.5) for rg in rgv]
    upper_scale = xr_icurve.get_max_y() * 1000
    bounds += [(1e-3, upper_scale) for _ in range(num_components)]

    method = 'Nelder-Mead'
    if model_params is not None:
        method = model_params.get('method', 'Nelder-Mead')

    result = minimize(objective_function, initial_guess, bounds=bounds, method=method)

    if debug:
        print(f"Lognormal optimization: {_eval_count[0]} evals, success={result.success}")
        print("N=%g, T=%g, x0=%g, tI=%g, N0=%g, k=%g, mu=%g, sigma=%g" % tuple(result.x[0:8]))
        print("Rgs:", result.x[8:8 + num_components])
        print("Scales:", result.x[8 + num_components:8 + 2 * num_components])

    N_, T_, x0_, tI_, N0_, k_, mu_, sigma_ = result.x[0:8]
    rgv_ = result.x[8:8 + num_components]
    scales_ = result.x[8 + num_components:8 + 2 * num_components]

    column = SdmColumn([N_, T_, me, mp, x0_, tI_, N0_, mu_, sigma_, k_],
                       pore_dist='lognormal', rt_dist=rt_dist)

    if debug:
        print("initial_scales:", scales_init)
        print("optimized scales:", list(scales_))
        print("optimized k:", k_)
        print("optimized mu:", mu_, "sigma:", sigma_)

    new_xr_ccurves = []
    for rg, scale in zip(rgv_, scales_):
        ccurve = SdmComponentCurve(x, column, rg, scale)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves

def adjust_rg_and_poresize(sdm_decomposition, rgcurve=None):
    """ Adjust rg and poresize in the decomposition based on the optimized component curves.
    """
    from .SdmComponentCurve import SdmColumn
    rgs = np.array(sdm_decomposition.get_rgs())     # get SAXS rgs
    xr_ccurves = sdm_decomposition.xr_ccurves
    column = xr_ccurves[0].column
    column_params = column.get_params()
    # params: (N, T, me, mp, x0, tI, N0, poresize, timescale, k)
    poresize = column_params[7]
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

    new_column_params = list(column_params)
    new_column_params[7] = new_poresize
    new_column = SdmColumn(new_column_params, pore_dist=column.pore_dist, rt_dist=column.rt_dist)
    for i, ccurve in enumerate(xr_ccurves):
        ccurve.column = new_column
        ccurve.rg = rhov[i] * new_poresize
        



 