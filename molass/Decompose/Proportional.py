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
# mirrors molass_legacy.ObjectiveFunctions.G0346's TAU_BOUND_RATIO setting (default 0.65):
# |tau| <= sigma*TAU_BOUND_RATIO. Kept as a local constant so this module stays legacy-free.
TAU_BOUND_RATIO = 0.65
# Martin-Synge plate theory self-consistency: mu_i = N*w_i - tI, w_i=sqrt(sigma_i**2+tau_i**2).
# N is self-estimated per-evaluation (exact solve at num_components=2, least-squares OLS at
# num_components>=3), clamped >=0 (width shouldn't shrink as retention grows). Self-estimation
# is a free rider when it succeeds -- the residual is always ~0 at num_components=2, and only
# mildly informative just above -- so it never distorts a dataset whose components are already
# mutually consistent under SOME plate count. Only when self-estimation fails (near-identical
# widths -> N undefined, or a negative width/retention correlation -> N clamped to 0) does it
# fall back to a fixed N=sqrt(num_plates), which is a genuine constant and yields a real,
# non-degenerate penalty (see molass-researcher 40_initial_penalties math discussion).
PLATE_PENALTY_SCALE = 1.0
DEFAULT_NUM_PLATES = 14400

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

def decompose_proportionally(icurve, proportions, debug=False, allow_negative_peaks=False, use_plate_penalty=False, num_plates=None):
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
    use_plate_penalty : bool, optional
        If True, add a Martin-Synge plate-count self-consistency penalty (see
        PLATE_PENALTY_SCALE comment below). Verified to help some datasets (e.g. more
        even proportions across many components) but hurt others (e.g. Y17's 3-component
        case, where per-component Rg estimation is inherently less stable) -- not safe as
        an always-on default, so opt-in. Default is False.
    num_plates : int, optional
        Fallback plate count used only when self-estimating N fails (near-identical
        component widths, or a negative width/retention correlation). See
        DEFAULT_NUM_PLATES / the plate_penalty comment in this module for details.
        Default is None (uses DEFAULT_NUM_PLATES=14400). Ignored if use_plate_penalty=False.

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
        tau_violation = 0.0
        mus = []
        ws = []
        for params in params_all.reshape(shape):
            m, s, t = params[1:4]
            cy = egh(x, *params)
            cy_list.append(cy)
            areas.append(np.sum(cy))
            # keep the joint fit's own tau consistent with its own sigma, not just the
            # initial slice's std (see molass-library#264 / the tau bound box below)
            tau_violation += max(0, abs(t) - TAU_BOUND_RATIO * s) ** 2
            mus.append(m)
            ws.append(np.hypot(s, t))
        ty = np.sum(cy_list, axis=0)
        props = np.array(areas)/np.sum(areas)
        if return_props:
            return props
        if debug_ax is not None:
            debug_ax.plot(x, ty, color='red', alpha=0.3)

        # shared-plate-count self-consistency (opt-in, see use_plate_penalty docstring):
        # self-estimate N (exact at num_components=2, least-squares at num_components>=3);
        # fall back to a fixed N when that estimate is undefined or unphysical (see
        # PLATE_PENALTY_SCALE comment above).
        plate_penalty = 0.0
        if use_plate_penalty:
            mu_arr = np.array(mus)
            w_arr = np.array(ws)
            w_var = np.var(w_arr)
            N_fallback = np.sqrt(num_plates if num_plates is not None else DEFAULT_NUM_PLATES)
            if w_var > VERY_SMALL_VALUE:
                N_star = np.cov(w_arr, mu_arr, bias=True)[0, 1] / w_var
                N_use = N_star if N_star > 0 else N_fallback
            else:
                N_use = N_fallback
            c_use = np.mean(mu_arr) - N_use * np.mean(w_arr)
            plate_penalty = np.var(mu_arr - (N_use * w_arr + c_use))

        return (safe_log10(np.sum((ty - y) ** 2))
                + 0.1 * safe_log10(np.sum((props - proportions)**2))
                + 0.1 * safe_log10(1 + TAU_PENALTY_SCALE * tau_violation)
                + 0.1 * safe_log10(1 + PLATE_PENALTY_SCALE * plate_penalty))

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
