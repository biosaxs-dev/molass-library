"""
    Mapping.SimpleMapperpy
"""
import numpy as np
from scipy.stats import linregress
from sklearn.linear_model import LinearRegression
from molass.Mapping.MappingInfo import MappingInfo

ACCEPTABLE_COVERAGE_RATIO = 0.50    # < 0.57 for 20201005_1
RELIABLE_COVERAGE_RATIO = 0.60      # < 0.70 for 20201006_1, < 0.80 for 20200125_1, < 0.80 for 20200125_2
ACCEPTABLE_2SIGMA_RATIO = 0.05      #

def compute_mapping_coverage(x, y, slope, intercept, debug=False):
    """
    Compute the coverage ratio of the mapping from x to y.
    The coverage ratio is defined as the ratio of the overlapping range
    of the mapped x values and the y values to the total range of x values.
    
    Parameters
    ----------
    x : array-like
        The x values.
    y : array-like
        The y values.
    slope : float
        The slope of the mapping line.
    intercept : float
        The intercept of the mapping line.
    debug : bool, optional
        If True, print debug information.

    Returns
    -------
    coverage_ratio : float
        The coverage ratio of the mapping.
    """
    y_ = x[[0,-1]]*slope + intercept
    ymin = max(y[0], y_[0])
    ymax = min(y[-1], y_[1])
    x_ = (ymin - intercept) / slope, (ymax - intercept) / slope
    xmin = max(x[0], x_[0])
    xmax = min(x[-1], x_[1])
    coverage_ratio = (xmax - xmin) / (x[-1] - x[0]) 
    return coverage_ratio

def estimate_slope_reliability(xr_curve, x, uv_curve, y, coverage_ratio, debug=False):
    """
    Estimate the reliability of the slope based on coverage ratio and peak ratio.
    This is particularly important when there is only one peak in the curves.

    Parameters
    ----------
    xr_curve : Curve
        The X-ray curve.
    x : array-like
        The x values of the peak (mean - std, mean, mean + std).
    uv_curve : Curve
        The UV curve.
    y : array-like
        The y values of the peak (mean - std, mean, mean + std).
    coverage_ratio : float
        The coverage ratio of the mapping.
    debug : bool, optional
        If True, print debug information.

    Returns
    -------
    reliable : bool
        True if the slope is considered reliable, False otherwise.
    """
    if coverage_ratio >= RELIABLE_COVERAGE_RATIO:
        # as in 20201006_1, 20200125_1, 20200125_2
        return True
    else:
        # as in 20201006_1
        pass
    
    rx_peak_ratio = (x[2] - x[0]) / (xr_curve.x[-1] - xr_curve.x[0])
    uv_peak_ratio = (y[2] - y[0]) / (uv_curve.x[-1] - uv_curve.x[0])
    peak_ratio = min(rx_peak_ratio, uv_peak_ratio)
    if debug:
        print(f"estimate_slope_reliability: peak_ratio={peak_ratio}")
    return peak_ratio >= ACCEPTABLE_2SIGMA_RATIO

def compute_mapping_by_full_coverage(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=False):
    """
    Compute the mapping by using the full coverage of the curves.
    This is used when there is only one peak in the curves.
    The mapping is computed by linear regression using three points:
        (mean - std, mean, mean + std)
    The peak point is given more weight than the edges.
    The peak point is determined by the first peak in the curves:

    Parameters
    ----------
    xr_curve : Curve
        The X-ray curve.
    xr_peaks : list of int
        The peak positions in the X-ray curve.
    uv_curve : Curve
        The UV curve.
    uv_peaks : list of int
        The peak positions in the UV curve.
    debug : bool, optional
        If True, print debug information.

    Returns
    -------
    mapping : MappingInfo
        The computed mapping information.
    """
    px = xr_curve.x[xr_peaks[0]]
    py = uv_curve.x[uv_peaks[0]]
    """
    py = px * slope + intercept
    Y = X * slope + intercept
        where  (X,Y) == (xr_curve.x[0], uv_curve.x[0])
            or (X,Y) == (xr_curve.x[-1], uv_curve.x[-1])
    """
    X = np.array([xr_curve.x[0], px, xr_curve.x[-1]]).reshape(3, 1)
    y = np.array([uv_curve.x[0], py, uv_curve.x[-1]])

    reg = LinearRegression().fit(X, y,
                                 sample_weight=[0.1, 0.8, 0.1],   # peak top is more important than the edges
                                 )
    slope = reg.coef_[0]
    intercept = reg.intercept_

    if debug:
        print("X=", X.flatten())
        print("y=", y)
        print("compute_mapping_by_full_coverage: slope=", slope, "intercept=", intercept)
    return MappingInfo(slope, intercept, xr_peaks, uv_peaks, None, None, xr_curve, uv_curve)

PEAK_CORE_FRACTION = 0.5    # the core of a peak: the contiguous region above this fraction of its height
MIN_CORE_POINTS = 3

def peak_position_with_sd(x, y, i, fraction=PEAK_CORE_FRACTION):
    """
    The refined position of the peak at index i and its noise-propagated standard deviation.

    See :func:`refine_peak_position`. The standard deviation propagates the noise of ``y``
    (estimated from the second differences, robustly) through the centroid; it ignores the
    dependence of the core limits on the noise. When the position falls back to ``x[i]``
    the standard deviation is half a sample spacing.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    fallback = (float(x[i]), 0.5 * float(np.median(np.diff(x))) if len(x) > 1 else 0.5)
    level = fraction * y[i]
    if not y[i] > 0:
        return fallback
    lo = hi = i
    while lo > 0 and y[lo - 1] >= level:
        lo -= 1
    while hi < len(y) - 1 and y[hi + 1] >= level:
        hi += 1
    if lo == 0 or hi == len(y) - 1 or hi - lo + 1 < MIN_CORE_POINTS:
        return fallback
    w = y[lo:hi + 1] - level
    xs = x[lo:hi + 1]
    position = float(np.sum(xs * w) / np.sum(w))
    d2 = y[:-2] - 2 * y[1:-1] + y[2:]
    sigma = 1.4826 * float(np.median(np.abs(d2 - np.median(d2)))) / np.sqrt(6)
    sd = sigma * float(np.sqrt(np.sum((xs - position)**2))) / float(np.sum(w))
    return position, sd

def refine_peak_position(x, y, i, fraction=PEAK_CORE_FRACTION):
    """
    Estimate the position of the peak at index i with sub-frame resolution (molass-library#328).

    The apex index of a noisy curve is only good to about one frame, which limits a mapping
    fitted through apexes accordingly. The centroid of the peak core (the contiguous region
    above ``fraction`` of the peak height, weighted by the excess over that level) is
    several times less noise-sensitive.

    Parameters
    ----------
    x, y : array-like
        The curve.
    i : int
        The index of the (integer) peak position.
    fraction : float, optional
        The core is the region above this fraction of the peak height.

    Returns
    -------
    position : float
        The refined peak position in the units of x. Falls back to ``x[i]`` when the core
        is cut by the edge of the curve or too narrow.
    """
    return peak_position_with_sd(x, y, i, fraction)[0]

def estimate_resolution_frames(x, sdx, y, sdy, xr_range, num_samples=200, seed=0):
    """
    Rough uncertainty of a mapping fitted through the peak positions, in XR frames (molass-library#337).

    The positions are perturbed by their standard deviations and the mapping is refitted;
    the result is the rms, over the perturbations, of the equivalent XR-frame shift of the
    mapping at the middle of ``xr_range``.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    rng = np.random.default_rng(seed)
    slope, intercept = linregress(x, y)[0:2]
    mid = 0.5 * (xr_range[0] + xr_range[1])
    shifts = []
    for _ in range(num_samples):
        s, b = linregress(x + rng.normal(0, sdx), y + rng.normal(0, sdy))[0:2]
        shifts.append(((s - slope) * mid + (b - intercept)) / slope)
    return float(np.sqrt(np.mean(np.square(shifts))))

def estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, retry=True, debug=False):
    """
    Estimate the mapping between xr_curve and uv_curve using the given peak positions.
    The mapping is computed by linear regression using the peak positions.
    If the coverage ratio is not acceptable, it retries with corrected curves.
    Parameters
    ----------
    xr_curve : Curve
        The X-ray curve.
    xr_peaks : list of int
        The peak positions in the X-ray curve.
    uv_curve : Curve
        The UV curve.
    uv_peaks : list of int
        The peak positions in the UV curve.
    retry : bool, optional
        If True, retries with corrected curves if the coverage ratio is not acceptable.
        Default is True.
    debug : bool, optional
        If True, print debug information.

    Returns
    -------
    mapping : MappingInfo
        The estimated mapping information.
    """
    resolution_frames = None
    if len(xr_peaks) > 1:
        # sub-frame positions: the integer apex limits the mapping to about one frame (#328)
        xr_fits = [peak_position_with_sd(xr_curve.x, xr_curve.y, i) for i in xr_peaks]
        uv_fits = [peak_position_with_sd(uv_curve.x, uv_curve.y, i) for i in uv_peaks]
        x = np.array([p for p, _ in xr_fits])
        y = np.array([p for p, _ in uv_fits])
        xr_moment = None
        uv_moment = None
        resolution_frames = estimate_resolution_frames(x, [s for _, s in xr_fits], y, [s for _, s in uv_fits],
                                                       (xr_curve.x[0], xr_curve.x[-1]))

    elif len(xr_peaks) == 1:
        from molass.Stats.EghMoment import EghMoment
        xr_moment = EghMoment(xr_curve, num_peaks=1)
        M, std = xr_moment.get_meanstd()
        x = [M - std, M, M + std]
        uv_moment = EghMoment(uv_curve, num_peaks=1)
        M, std = uv_moment.get_meanstd()
        y = [M - std, M, M + std]

    slope, intercept = linregress(x, y)[0:2]
    coverage_ratio = compute_mapping_coverage(xr_curve.x, uv_curve.x, slope, intercept)
    if debug:
        print(f"Mapping coverage: {coverage_ratio}")
    if coverage_ratio >= ACCEPTABLE_COVERAGE_RATIO:
        if xr_moment is not None:
            # that is a case where we have only one peak in xr_curve
            assert len(xr_peaks) == 1, "xr_peaks should have only one peak."
            assert len(x) == 3, "x should have three elements."
            assert len(y) == 3, "y should have three elements."
            reliable = estimate_slope_reliability(xr_curve, x, uv_curve, y, coverage_ratio, debug=debug)
            if not reliable:
                return compute_mapping_by_full_coverage(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)

        return MappingInfo(slope, intercept, xr_peaks, uv_peaks, xr_moment, uv_moment, xr_curve, uv_curve,
                           resolution_frames=resolution_frames)
    else:
        assert retry, "Mapping coverage is not acceptable after retry."
        xr_curve_ = xr_curve.corrected_copy()
        uv_curve_ = uv_curve.corrected_copy()
        return estimate_mapping_for_matching_peaks(xr_curve_, xr_peaks, uv_curve_, uv_peaks, retry=False, debug=debug)

def estimate_mapping_impl(xr_curve, uv_curve, debug=False):
    """
    Estimate the mapping between xr_curve and uv_curve.
    The mapping is computed by identifying groupable peaks in both curves,
    matching them, and then performing linear regression on the matched peaks.

    Parameters
    ----------
    xr_curve : Curve
        The X-ray curve.
    uv_curve : Curve
        The UV curve.
    debug : bool, optional
        If True, print debug information.
        
    Returns
    -------
    mapping : MappingInfo
        The estimated mapping information.
    """
    from molass.Mapping.Grouping import get_groupable_peaks

    xr_peaks, uv_peaks = get_groupable_peaks(xr_curve, uv_curve, debug=debug)
    if debug:
        print(f"Peaks: xr_peaks={xr_peaks}, uv_peaks={uv_peaks}")

    # Always run the shape-correlation matcher, even when raw peak counts already
    # agree: equal counts can still hide a case where a peak on EACH side has no
    # counterpart in the other channel (e.g. one species with no UV signal plus one
    # spurious/noise UV peak) -- KMeans grouping alone can't recognize that and will
    # force a wrong 1:1 pairing. See EcoCas3, molass-library#270.
    from importlib import reload
    import molass.Mapping.PeakMatcher
    reload(molass.Mapping.PeakMatcher)
    from molass.Mapping.PeakMatcher import select_matching_peaks
    xr_peaks, uv_peaks = select_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)
    if debug:
        import matplotlib.pyplot as plt
        print("xr_peaks=", xr_peaks)
        print("uv_peaks=", uv_peaks)
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10,4))
        fig.suptitle("selected matching peaks")
        for ax, curve, peaks in [(ax1, uv_curve, uv_peaks), (ax2, xr_curve, xr_peaks)]:
            ax.plot(curve.x, curve.y)
            ax.plot(curve.x[peaks], curve.y[peaks], 'o')
        plt.show()

    try:
        return estimate_mapping_for_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)
    except:
        from molass_legacy.KekLib.ExceptionTracebacker import log_exception
        log_exception(None, "Failed to estimate mapping for matching peaks.", n=5)
        if len(xr_peaks) == 1:
            return compute_mapping_by_full_coverage(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=debug)
        else:
            raise ValueError(
                "Failed to estimate mapping for matching peaks. "
            )