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
SIGNAL_THRESHOLD_RATIO = 0.2
MIN_SIGNAL_POINTS = 5

def safe_log10(x):
    """Compute the base-10 logarithm of x, ensuring numerical stability.
    Parameters
    ----------
    x : float or array-like
        The input value(s) for which to compute the logarithm.

    Returns
    -------
    float or array-like
        The base-10 logarithm of the input value(s), with a lower bound to avoid
        logarithm of zero or negative values."""
    return np.log10(np.maximum(x, VERY_SMALL_VALUE))

def get_proportional_slices(x, y, proportions, debug_ax=None):
    """
    Get slices of x and y based on the specified proportions.
    Each slice corresponds to a component whose area is proportional to the given proportions.

    Parameters
    ----------
    x : array-like
        The x values of the data.
    y : array-like
        The y values of the data.
    proportions : array-like
        The proportions for each component. Should sum to 1.
    debug_ax : matplotlib.axes.Axes, optional
        An optional axis for debugging plots. If provided, the cumulative curve and slice boundaries
        will be plotted on this axis.

    Returns
    -------
    list of slice
        A list of slices corresponding to the proportional areas of each component.
    """
    proportions = np.asarray(proportions)
    proportions = proportions / proportions.sum()

    nny = y.copy()
    nny[nny < 0] = 0   # always clip for cumulative-area slicing (initialization only)
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
        stop = int(np.searchsorted(x, x_))
        xslices.append(slice(start, stop))
        start = stop
    stop = None
    xslices.append(slice(start, stop))
    return xslices

def estimate_initial_params(x, y, moment, allow_negative=False):
    """
    Estimate initial parameters for the egh function based on the given data and moment.

    Parameters
    ----------
    x : array-like
        The x values of the data.
    y : array-like
        The y values of the data.
    moment : Moment
        The moment object containing statistical information about the data.
    allow_negative : bool, optional
        If True, allow negative peak heights. Default is False.

    Returns
    -------
    params : array-like
        The estimated parameters for the egh function: (height, mean, std, tau).
    """
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
    if allow_negative:
        bounds = [(-2*abs(h), 2*abs(h)), (mean-std, mean+std), (0, max_std), (-std, +std)]
    else:
        bounds = [(0, 2*h), (mean-std, mean+std), (0, max_std), (-std, +std)]
    result = minimize(objective, x0=initial_params, method='Nelder-Mead', bounds=bounds)
    return result.x

def restrict_to_signal(x, y, amp_ref, threshold_ratio=SIGNAL_THRESHOLD_RATIO, min_points=MIN_SIGNAL_POINTS):
    """
    Restrict (x, y) to the sub-region where |y| exceeds a fraction of a reference amplitude.

    A proportional slice can span a long stretch of near-zero background alongside only a
    small piece of real signal (e.g. when num_components exceeds the true peak count).
    Computing a moment/EGH fit over the whole slice in that case anchors the mean/std on
    the background instead of the real peak, which then boxes the joint optimizer's bounds
    away from the true peak location entirely. Restricting to the signal-bearing sub-region
    avoids this.

    Parameters
    ----------
    x, y : array-like
        The x and y values of the slice.
    amp_ref : float
        Reference amplitude (typically the full curve's peak height) that `threshold_ratio`
        is relative to -- using a slice-local reference would be circular for slices that
        contain no real signal at all.
    threshold_ratio : float, optional
        Points with |y| below `threshold_ratio * amp_ref` are excluded. Default 0.2.
    min_points : int, optional
        Minimum number of points required to accept the restriction; falls back to the
        unrestricted (x, y) otherwise -- e.g. a slice that is genuinely pure background
        rather than a partial peak. Default 5.

    Returns
    -------
    x, y : array-like
        The restricted (or, on fallback, original) arrays.
    """
    mask = np.abs(y) > threshold_ratio * amp_ref
    if np.count_nonzero(mask) < min_points:
        return x, y
    return x[mask], y[mask]

def debug_plot(ax, x, xslices, plot_params):
    """
    Plot the initial decomposition parameters for debugging.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axis on which to plot the debug information.
    x : array-like
        The x values of the data.
    xslices : list of slice
        The slices corresponding to each component.
    plot_params : array-like
        The parameters for each component to be plotted.

    Returns
    -------
    None
    """
    for k, sl in enumerate(xslices):
        params = plot_params[k]
        if sl.stop is not None:
            ax.axvline(x=sl.stop, color='gray', linestyle=':', alpha=0.5)
        ax.plot(x, egh(x, *params), linestyle=':')

def decompose_proportionally(icurve, proportions, debug=False, allow_negative_peaks=False):
    """
    Decompose the given data (x, y) into components based on the specified proportions.
    Each component is modeled using the egh function from molass.SEC.Models.Simple.

    Parameters
    ----------
    icurve : ICurve
        The intensity elution curve to be decomposed.
    proportions : array-like
        The proportions for each component. Should sum to 1.
    debug : bool, optional
        If True, enable debug mode to visualize the decomposition process.
        Default is False.

    Returns
    -------
    result : OptimizeResult
        The result of the optimization containing the optimized parameters.            
    """

    x, y = icurve.get_xy()

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
    amp_ref = np.max(np.abs(y))
    signal_xy = [restrict_to_signal(x[s], y[s], amp_ref) for s in xslices]
    moments = [Moment(xr, yr) for xr, yr in signal_xy]
    initial_params = np.array([estimate_initial_params(xr, yr, m, allow_negative=allow_negative_peaks) for (xr, yr), m in zip(signal_xy, moments)])
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
        if allow_negative_peaks:
            h_abs = abs(initial_params[i, 0])
            bounds.append((-2*h_abs, 2*h_abs))
            scale_bounds.append((-2*h_abs, 2*h_abs))
        else:
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
