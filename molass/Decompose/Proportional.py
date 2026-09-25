"""
Decompose.Proportional.py
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
from molass.Stats.Moment import Moment
from molass.SEC.Models.Simple import egh
from molass.SEC.Models.MartinSynge import compute_sigma, tI_bounds, N_LOWER_BOUND, N_UPPER_BOUND
from scipy.optimize import minimize

VERY_SMALL_VALUE = 1e-10
TAU_PENALTY_SCALE = 1e5
SIGNAL_THRESHOLD_RATIO = 0.2
MIN_SIGNAL_POINTS = 5
# mirrors molass_legacy.ObjectiveFunctions.G0346's TAU_BOUND_RATIO setting (default 0.65):
# |tau| <= sigma*TAU_BOUND_RATIO. Kept as a local constant so this module stays legacy-free.
TAU_BOUND_RATIO = 0.65
# components must stay in elution order; mirrors LowRank.CurveDecomposer's mean_order_penalty.
MEAN_ORDER_PENALTY_SCALE = 1e5
# the order penalty alone only forbids crossing (a negative gap) -- it does NOT forbid two
# components converging to the exact same tR (a zero gap), which is a real, observed
# failure mode (component collapse, confirmed empirically 2026-09-25: Y17AH20N
# proportions=[6,2,1,1] converges two of its four components to identical params). This
# ratio sets a required minimum gap, relative to the smallest gap already present in the
# Stage-1 naive slice means (so it doesn't force separation wider than the slicing itself
# suggests, but does forbid full collapse).
MIN_SEPARATION_RATIO = 0.3
# hard floor on the Martin-Synge-derived sigma, in units of frame spacing: no real
# chromatographic peak is sub-multi-frame narrow. Without this, nothing stops sigma from
# collapsing toward zero (with tau compensating) once tR drifts close to tI -- confirmed
# empirically in molass-researcher/experiments/43_martin_synge_constraint (2026-09-25).
SIGMA_MIN_PENALTY_SCALE = 1e5
SIGMA_MIN_FRAMES = 3.0
# Stage 2 tries a full fit from each of these plate-count candidates and keeps whichever
# gives the lowest objective, rather than a single Nelder-Mead run from one seed. A single
# run (with or without log-N reparameterization or basinhopping restarts) was repeatedly
# unable to reliably escape a bad-scale local optimum -- confirmed empirically the good,
# low-residual solution scores far lower on the SAME objective, so this is a search
# failure, not a formulation problem (molass-researcher/experiments/43_martin_synge_constraint,
# 2026-09-25). Costs ~5-10x one Nelder-Mead run (still ~1-2s per candidate).
DEFAULT_N_CANDIDATES = [100, 300, 1000, 3000, 10000, 30000, 100000]

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

def moment_match_initial_params(y, moment, allow_negative=False):
    """
    Set the initial EGH parameters to exactly match a slice's own (mean, std) moments --
    mu=mean, sigma=std, tau=0 (no skew moment is available to solve for tau, so it starts
    at 0, established here before Martin-Synge or any joint fit touches it). A direct
    assignment, not an optimization: replaces the previous per-slice Nelder-Mead sub-fit,
    which could hand the joint fit an already-inconsistent nonzero tau as its seed.

    Parameters
    ----------
    y : array-like
        The y values of the slice (signal-restricted).
    moment : Moment
        The moment object containing statistical information about the slice.
    allow_negative : bool, optional
        If True, allow a negative peak height when the slice's extremum is negative.
        Default is False.

    Returns
    -------
    params : array-like
        The initial parameters for the egh function: (height, mean, std, tau=0).
    """
    mean, std = moment.get_meanstd()
    if allow_negative:
        h = y[np.argmax(np.abs(y))]
    else:
        h = np.max(y)
    return np.array([h, mean, std, 0.0])

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

def decompose_proportionally(icurve, proportions, debug=False, allow_negative_peaks=False, num_plates=None):
    """
    Decompose the given data (x, y) into components based on the specified proportions.
    Each component is modeled using the egh function from molass.SEC.Models.Simple.

    Sigma (Gaussian width) is not fit independently per component -- it is derived from
    a shared injection time and plate count via Martin-Synge plate theory (see
    molass.SEC.Models.MartinSynge): sigma_i = (tR_i - tI) / sqrt(N). This is why the
    later-eluting component cannot be narrower than the theory allows (molass-library#264).

    Parameters
    ----------
    icurve : ICurve
        The intensity elution curve to be decomposed.
    proportions : array-like
        The proportions for each component. Should sum to 1.
    debug : bool, optional
        If True, enable debug mode to visualize the decomposition process.
        Default is False.
    num_plates : int, optional
        Extra plate-count candidate added to Stage 2's grid search (see
        DEFAULT_N_CANDIDATES), in case a known/expected value isn't already spanned by
        the default grid. Default is None (uses DEFAULT_N_CANDIDATES only).

    Returns
    -------
    result : OptimizeResult
        The result of the optimization containing the optimized (H, tR, sigma, tau)
        parameters per component (sigma reconstructed from the fitted tI, N).
    """

    x, y = icurve.get_xy()
    dx = float(np.median(np.diff(x)))

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
    initial_params = np.array([moment_match_initial_params(yr, m, allow_negative=allow_negative_peaks) for (xr, yr), m in zip(signal_xy, moments)])

    if debug:
        debug_plot(ax1, x, xslices, initial_params)

    num_components = len(proportions)
    method = 'Nelder-Mead'
    # Stage-1 slices are contiguous and non-overlapping, so their naive means are already
    # strictly increasing -- their smallest gap sets the minimum-separation floor below.
    min_separation = MIN_SEPARATION_RATIO * np.min(np.diff(initial_params[:,1])) if num_components > 1 else 0.0

    # shared plate-theory parameters come first (tI, N), followed by each component's
    # own (H, tR, tau); sigma is never a free parameter -- see module docstring.
    tI_lo, tI_hi = tI_bounds(initial_params[:,1])
    bounds = [(tI_lo, tI_hi), (N_LOWER_BOUND, N_UPPER_BOUND)]
    for i in range(num_components):
        if allow_negative_peaks:
            h_abs = abs(initial_params[i, 0])
            bounds.append((-2*h_abs, 2*h_abs))
        else:
            bounds.append((0, 2*initial_params[i, 0]))
        mean, std = moments[i].get_meanstd()
        bounds.append((mean-std, mean+std))
        bounds.append((-std, +std))

    def total_objective(params_all, debug_ax=None, return_props=False):
        tI, N = params_all[0], params_all[1]
        cy_list = []
        areas = []
        tau_violation = 0.0
        sigma_min_violation = 0.0
        tR_list = []
        sigma_min = SIGMA_MIN_FRAMES * dx
        for h, tR, t in params_all[2:].reshape(num_components, 3):
            s_raw = compute_sigma(tR, tI, N)
            s = max(s_raw, VERY_SMALL_VALUE)
            # penalize (not silently clip) sigma collapsing toward zero -- see
            # SIGMA_MIN_PENALTY_SCALE comment above
            sigma_min_violation += max(0, sigma_min - s_raw) ** 2
            cy = egh(x, h, tR, s, t)
            cy_list.append(cy)
            areas.append(np.sum(cy))
            # keep tau a bounded modification of the plate-derived sigma, not
            # a co-equal width parameter (see molass-library#264 discussion)
            tau_violation += max(0, abs(t) - TAU_BOUND_RATIO * s) ** 2
            tR_list.append(tR)
        ty = np.sum(cy_list, axis=0)
        props = np.array(areas)/np.sum(areas)
        if return_props:
            return props
        if debug_ax is not None:
            debug_ax.plot(x, ty, color='red', alpha=0.3)

        # components must stay in elution order AND meaningfully separated -- nothing else
        # enforces either (see MIN_SEPARATION_RATIO comment above)
        gaps = np.diff(tR_list) if num_components > 1 else np.array([])
        mean_order_penalty = np.sum(np.maximum(0, min_separation - gaps) ** 2)

        return (safe_log10(np.sum((ty - y) ** 2))
                + 0.1 * safe_log10(np.sum((props - proportions)**2))
                + 0.1 * safe_log10(1 + MEAN_ORDER_PENALTY_SCALE * mean_order_penalty)
                + 0.1 * safe_log10(1 + SIGMA_MIN_PENALTY_SCALE * sigma_min_violation)
                + 0.1 * safe_log10(1 + TAU_PENALTY_SCALE * tau_violation))

    # grid search over candidate plate counts -- see DEFAULT_N_CANDIDATES comment above
    # for why a single Nelder-Mead run from one seed is not reliable enough here.
    N_candidates = DEFAULT_N_CANDIDATES if num_plates is None else sorted(set(DEFAULT_N_CANDIDATES) | {num_plates})
    best_fun, result2 = None, None
    for N_cand in N_candidates:
        sqrtN_cand = np.sqrt(N_cand)
        tI_cand = np.mean(initial_params[:,1] - sqrtN_cand*initial_params[:,2])
        tI_cand = min(max(tI_cand, tI_lo), tI_hi)
        x0_cand = np.concatenate([[tI_cand, float(N_cand)], initial_params[:, [0, 1, 3]].flatten()])
        result_cand = minimize(total_objective, x0=x0_cand, method=method, bounds=bounds)
        if best_fun is None or result_cand.fun < best_fun:
            best_fun, result2 = result_cand.fun, result_cand

    if debug:
        total_objective(result2.x, debug_ax=ax1)
        props = total_objective(result2.x, return_props=True)
        print(props)

    # reconstruct the classic (H, tR, sigma, tau)-per-component flat layout that callers
    # (e.g. LowRank.QuickImplement) expect -- sigma is derived from the fitted tI, N.
    tI_final, N_final = result2.x[0], result2.x[1]
    comp_final = result2.x[2:].reshape(num_components, 3)
    classic_params = np.empty((num_components, 4))
    classic_params[:, 0] = comp_final[:, 0]
    classic_params[:, 1] = comp_final[:, 1]
    classic_params[:, 2] = compute_sigma(comp_final[:, 1], tI_final, N_final)
    classic_params[:, 3] = comp_final[:, 2]
    result2.x = classic_params.flatten()
    return result2
