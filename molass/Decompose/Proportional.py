"""
Decompose.Proportional.py
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
from molass.Stats.Moment import Moment
from molass.SEC.Models.Simple import egh
from scipy.optimize import minimize

VERY_SMALL_VALUE = 1e-10
TAU_RATIO_LIMIT = 0.5
TAU_PENALTY_SCALE = 1e5

def safe_log10(x):
    return np.log10(np.maximum(x, VERY_SMALL_VALUE))

def get_proportional_slices(x, y, proportions, debug_ax=None):
    proportions = np.asarray(proportions)
    proportions = proportions / proportions.sum()

    nny = y.copy()
    nny[nny < 0] = 0   # no negative values
    cy = np.cumsum(nny)

    cp = np.cumsum(proportions)*cy[-1]
    spline = UnivariateSpline(cy[nny > 0], x[nny > 0], s=0)
    xp = spline(cp)

    if debug_ax is not None:
        debug_ax.plot(x, cy)
        for y_, x_ in zip(cp, xp):
            debug_ax.axhline(y_, color='gray', linestyle=':', alpha=0.5)
            debug_ax.axvline(x_, color='gray', linestyle=':', alpha=0.5)

    xslices = []
    start = 0
    for x_ in xp[:-1]:
        stop = int(round(x_))
        xslices.append(slice(start, stop))
        start = stop
    stop = None
    xslices.append(slice(start, stop))
    return xslices

def estimate_initial_params(x, y, moment):
    # Estimate initial parameters for each slice
    mean, std = moment.get_meanstd()

    def objective(params):
        cy = egh(x, *params)
        return (np.log10(np.sum((cy - y) ** 2))
                + np.log10(max(VERY_SMALL_VALUE, TAU_PENALTY_SCALE* min(0, TAU_RATIO_LIMIT - abs(params[3]/params[2]))**2))
                )

    # Minimize the objective function
    h = np.max(y)
    initial_params = h, mean, std, 0.0
    max_std = 2 * std
    bounds = [(0, 2*h), (mean-std, mean+std), (0, max_std), (-std, +std)]
    result = minimize(objective, x0=initial_params, method='Nelder-Mead', bounds=bounds)
    return result.x

def debug_plot(ax, x, xslices, plot_params):
    for k, sl in enumerate(xslices):
        params = plot_params[k]
        if sl.stop is not None:
            ax.axvline(x=sl.stop, color='gray', linestyle=':', alpha=0.5)
        ax.plot(x, egh(x, *params), linestyle=':')

def decompose_proportionally(x, y, proportions, debug=False):
    if debug:
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
        fig.suptitle("Decomposition Debug Plots: %s" % (proportions,))
        ax1.plot(x, y, color='gray', alpha=0.5)
        debug_ax = ax2
    else:
        debug_ax = None
    proportions = np.asarray(proportions)/np.sum(proportions)
    xslices = get_proportional_slices(x, y, proportions, debug_ax=debug_ax)
    moments = [Moment(x[s], y[s]) for s in xslices]
    initial_params = np.array([estimate_initial_params(x[s], y[s], m) for s, m in zip(xslices, moments)])
    initial_params[:,0] *= 0.8

    if debug:
        debug_plot(ax1, x, xslices, initial_params)

    num_components = len(proportions)
    shape = (num_components, 4)

    def scale_objective(scales, debug_ax=None):
        cy_list = []
        for k, h in enumerate(scales):
            params = initial_params[k].copy()
            params[0] = h
            cy = egh(x, *params)
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        if debug_ax is not None:
            debug_ax.plot(x, ty, linestyle=':', color='red')
        return np.sum((ty - y) ** 2)

    bounds = []
    scale_bounds = []
    for i in range(num_components):
        bounds.append((0, 2*initial_params[i, 0]))
        scale_bounds.append((0, 2*initial_params[i, 0]))
        moment = moments[i]
        mean, std = moment.get_meanstd()
        bounds.append((mean-std, mean+std))
        bounds.append((0, 2*std))
        bounds.append((-std, +std))

    method = 'Nelder-Mead'
    result1 = minimize(scale_objective, x0=initial_params[:,0], method=method, bounds=scale_bounds)

    def total_objective(params_all, debug_ax=None, return_props=False):
        cy_list = []
        areas = []
        for params in params_all.reshape(shape):
            cy = egh(x, *params)
            cy_list.append(cy)
            areas.append(np.sum(cy))
        ty = np.sum(cy_list, axis=0)
        props = np.array(areas)/np.sum(areas)
        if return_props:
            return props
        if debug_ax is not None:
            debug_ax.plot(x, ty, color='red', alpha=0.3)
        return safe_log10(np.sum((ty - y) ** 2)) + 0.1 * safe_log10(np.sum((props - proportions)**2))

    if debug:
        scaled_params = initial_params.copy()
        scaled_params[:, 0] = result1.x
        total_objective(scaled_params.flatten(), debug_ax=ax1)
        props = total_objective(scaled_params.flatten(), return_props=True)
        print(props)

    result2 = minimize(total_objective, x0=initial_params.flatten(), method=method, bounds=bounds)
    if debug:
        props = total_objective(result2.x, return_props=True)
        print(props)
    return result2
