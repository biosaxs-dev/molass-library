"""
    Mapping.PeakMatcher.py
"""
import numpy as np
from itertools import combinations

# allowed RMS position residual of the peak-pairing line fit, in units of the median XR peak sigma;
# the correct pairing of proteins5 fits within 0.33, the wrong 3-peak pairing of EcoCas3 is off by 1.0
POSITION_TOLERANCE_SIGMA = 0.5
FWHM_PER_SIGMA = 2.355

def combination_pairs_of_size(m, n, k):
    """Yield all candidate (xr_index_subset, uv_index_subset) pairs of exactly k peaks each,
    preserving each side's relative (elution) order."""
    for xr_idx in combinations(range(m), k):
        for uv_idx in combinations(range(n), k):
            yield list(xr_idx), list(uv_idx)

def combination_pairs(m, n, min_k=2):
    """Yield all candidate (xr_index_subset, uv_index_subset) pairs of equal size k,
    for k = min(m, n) down to min_k, preserving each side's relative (elution) order.

    Generalizes the old m != n -only case (which always kept every peak from the
    smaller side) to also handle equal raw peak counts, and unequal counts where the
    smaller side may also contain a spurious peak that should be dropped -- both
    peaks may need discarding, not just the extras on the larger side
    (see EcoCas3, molass-library#270).
    """
    for k in range(min(m, n), min_k - 1, -1):
        yield from combination_pairs_of_size(m, n, k)

def get_smoothed_curve_y(curve):
    """Fit a smooth (EGH, negative-clipped) reconstruction of a curve's y-values, for
    shape comparison. Clipping negatives before the fit avoids raw baseline noise
    skewing the reconstruction (see EcoCas3 investigation, molass-library#270).
    """
    from molass.DataObjects.Curve import Curve
    from molass.Stats.EghMoment import EghMoment
    clipped = Curve(curve.x, np.clip(curve.y, 0, None), type='i')
    return EghMoment(clipped).get_y_()

def compute_shape_correlation(xr_curve, uv_curve, xr_peaks, uv_peaks, xr_y_smooth, uv_y_smooth):
    """Score a candidate peak-subset match by how well the two curves' shapes agree once
    mapped, instead of by peak-height agreement -- prominence is not preserved across
    UV/XR channels when components have different extinction ratios, which made the old
    height-weighted scoring pick the wrong correspondence for EcoCas3 (molass-library#270).

    Maps uv_curve onto xr_curve's frame axis using a candidate slope/intercept fit
    through the given peak pair(s), then compares the two (independently normalized)
    smoothed curves by Pearson correlation over their overlapping region.
    """
    xr_x = xr_curve.x
    uv_x = uv_curve.x
    x = xr_x[xr_peaks]
    y = uv_x[uv_peaks]
    slope, intercept = np.polyfit(x, y, 1)

    mapped_uv_x = (uv_x - intercept) / slope
    lo = max(xr_x[0], mapped_uv_x[0])
    hi = min(xr_x[-1], mapped_uv_x[-1])
    if hi <= lo:
        return -np.inf

    grid = np.linspace(lo, hi, 500)
    xr_on_grid = np.interp(grid, xr_x, xr_y_smooth)
    uv_on_grid = np.interp(grid, mapped_uv_x, uv_y_smooth)
    if xr_on_grid.max() <= 0 or uv_on_grid.max() <= 0:
        return -np.inf
    xr_n = xr_on_grid / xr_on_grid.max()
    uv_n = uv_on_grid / uv_on_grid.max()
    return np.corrcoef(xr_n, uv_n)[0, 1]

def estimate_peak_sigma(curve, peaks):
    """Median peak width of *peaks* (indices) as a Gaussian sigma in frames, from the full width at
    half maximum of the negative-clipped curve; ``None`` if no width can be determined."""
    from scipy.signal import peak_widths
    y = np.clip(np.asarray(curve.y, dtype=float), 0, None)
    widths = peak_widths(y, np.asarray(peaks, dtype=int), rel_height=0.5)[0] / FWHM_PER_SIGMA
    widths = widths[np.isfinite(widths) & (widths > 0)]
    return float(np.median(widths)) if len(widths) else None

def position_fit_rms(xr_x, uv_x):
    """RMS residual, in XR frames, of the straight line through paired peak positions (UV = a*XR + b).
    Returns ``(rms, slope, intercept)``."""
    slope, intercept = np.polyfit(xr_x, uv_x, 1)
    if slope <= 0:
        return np.inf, slope, intercept
    return float(np.sqrt(np.mean(((slope * xr_x + intercept - uv_x) / slope) ** 2))), slope, intercept

def select_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=False, tolerance_sigma=POSITION_TOLERANCE_SIGMA):
    """
    Select matching peaks between XR and UV curves.

    The peak *positions* decide first: a correct correspondence maps the XR peaks onto the UV
    peaks along one straight line. Starting from the largest possible subset (k = min(m, n)) and
    going down to k = 2, the first k for which some pairing fits a line to within
    ``tolerance_sigma`` times the typical XR peak width is taken; peaks may be dropped from either
    side, not just from whichever side has more raw peaks (see EcoCas3, molass-library#270).

    The whole-shape correlation of the two curves after mapping (see `compute_shape_correlation`)
    is used only to break ties, i.e. when positions cannot decide: k = 2 (any two pairs fit a line
    exactly) or several pairings of the same size within tolerance. Peak heights are never used --
    prominence is not preserved across UV/XR channels (#270).

    Parameters
    ----------
    xr_curve : Curve
        The XR curve object.
    xr_peaks : array-like
        The indices of the peaks in the XR curve.
    uv_curve : Curve
        The UV curve object.
    uv_peaks : array-like
        The indices of the peaks in the UV curve.
    debug : bool, optional
        If True, print debug information.
    tolerance_sigma : float, optional
        Allowed RMS position residual of the line fit, in units of the median XR peak sigma
        (default 0.5). If no peak width can be determined, the largest subset is taken.

    Returns
    -------
    tuple
        A tuple containing the selected matching peaks for XR and UV curves.
    """
    if debug:
        print("len(xr_peaks)=", len(xr_peaks))
        print("len(uv_peaks)=", len(uv_peaks))
    xr_peaks = np.asarray(xr_peaks)
    uv_peaks = np.asarray(uv_peaks)
    if len(xr_peaks) < 2 or len(uv_peaks) < 2:
        # not enough peaks on one side to fit a slope/intercept
        num = min(len(xr_peaks), len(uv_peaks))
        return xr_peaks[:num], uv_peaks[:num]

    sigma = estimate_peak_sigma(xr_curve, xr_peaks)
    tolerance = np.inf if sigma is None else tolerance_sigma * sigma
    if debug:
        print(f"position tolerance = {tolerance} frames (sigma={sigma})")
    xr_x = xr_curve.x[xr_peaks]
    uv_x = uv_curve.x[uv_peaks]

    for k in range(min(len(xr_peaks), len(uv_peaks)), 1, -1):
        fitting = []
        for index1, index2 in combination_pairs_of_size(len(xr_peaks), len(uv_peaks), k):
            rms, slope, _ = position_fit_rms(xr_x[index1], uv_x[index2])
            if debug:
                print(index1, index2, f"rms={rms:.2f} slope={slope:.4f}")
            if rms <= tolerance:
                fitting.append((index1, index2, rms))
        if not fitting:
            continue
        if k > 2 and len(fitting) == 1:
            index1, index2, rms = fitting[0]
        else:
            # positions cannot decide: let the curve shapes break the tie
            xr_y_smooth = get_smoothed_curve_y(xr_curve)
            uv_y_smooth = get_smoothed_curve_y(uv_curve)
            scored = [(compute_shape_correlation(xr_curve, uv_curve, xr_peaks[i1], uv_peaks[i2], xr_y_smooth, uv_y_smooth), i1, i2)
                      for i1, i2, _ in fitting]
            if debug:
                for corr, i1, i2 in scored:
                    print("tie-break", i1, i2, corr)
            _, index1, index2 = max(scored, key=lambda r: r[0])
        if debug:
            print(f"selected k={k}: xr_index={index1}, uv_index={index2}")
        return xr_peaks[index1], uv_peaks[index2]