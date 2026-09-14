"""
    Mapping.PeakMatcher.py
"""
import numpy as np
from itertools import combinations

def combination_pairs(m, n):
    assert m != n
    more_indeces = np.arange(max(m, n))
    num = min(m, n)
    less_indeces = np.arange(num)
    for c in combinations(more_indeces, num):
        if m > n:
            yield list(c), less_indeces
        else:
            yield less_indeces, list(c)

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

def select_matching_peaks(xr_curve, xr_peaks, uv_curve, uv_peaks, debug=False):
    """
    Select matching peaks between XR and UV curves.

    Scores each candidate peak-subset correspondence by whole-shape correlation after
    mapping (see `compute_shape_correlation`), not by peak-height agreement -- see
    molass-library#270 for why the latter is unreliable.

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
    xr_y_smooth = get_smoothed_curve_y(xr_curve)
    uv_y_smooth = get_smoothed_curve_y(uv_curve)

    # evaluate all the combination pairs
    score_recs = []
    for index1, index2 in combination_pairs(len(xr_peaks), len(uv_peaks)):
        corr = compute_shape_correlation(xr_curve, uv_curve, xr_peaks[index1], uv_peaks[index2], xr_y_smooth, uv_y_smooth)
        if debug:
            print(index1, index2, corr)
        score_recs.append((index1, index2, corr))

    score_recs = sorted(score_recs, key=lambda x: x[2], reverse=True)
    index1, index2, corr = score_recs[0]   # the record with highest shape correlation
    return xr_peaks[index1], uv_peaks[index2]