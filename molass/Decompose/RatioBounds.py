"""
Decompose.RatioBounds.py

Shared "prevent collapse via group consistency" bound for per-component ratios (e.g.
UV/XR height ratios). Given one ratio per component, returns a single [lower, upper]
band -- robust median + k*MAD in log space when there's more than one component,
or a fixed symmetric factor around the lone value otherwise (no group to compare
against -- see molass-library issue #271 discussion).

Calibrated using SAMPLE1's default (XR-first) 3-component decomposition: its ratios
spanned 2.22-4.98 (median 3.37, MAD(log ratio)=0.389) purely from real per-species
UV/XR contrast differences, not pathology. k=3 gives a band of ~[1.05, 10.8] for that
case -- wide enough to never clip legitimate variation like that, while still
rejecting order-of-magnitude collapses (e.g. a ratio of -19.8 or ~0).

Used by molass.Decompose.Partner.map_params_to_partner() and
molass.SEC.Models.UvOptimizer.optimize_uv_decomposition().
"""
import numpy as np

DEFAULT_K = 3.0
# no sibling component to compare against -- bound around the single ratio itself
# rather than a fixed universal default, so it still reflects that specific case.
SINGLE_COMPONENT_FACTOR = 3.0
MIN_FLOOR = 1e-6


def compute_ratio_bounds(ratios, k=DEFAULT_K, single_factor=SINGLE_COMPONENT_FACTOR, min_floor=MIN_FLOOR):
    """
    Compute a single [lower, upper] band for a set of per-component ratios, using
    robust group statistics when possible.

    Parameters
    ----------
    ratios : array-like
        One ratio per component (e.g. an initial UV/XR height-ratio guess). Must be
        the same *kind* of ratio across components for the group statistic to be
        meaningful.
    k : float, optional
        Band half-width in MAD units (median absolute deviation of log(ratios)).
        Default 3.0 -- see module docstring for calibration.
    single_factor : float, optional
        Symmetric factor used when there's only one ratio (or all ratios are
        ~identical, making MAD ~0) -- band becomes ``[ratio/single_factor,
        ratio*single_factor]``. Default 3.0.
    min_floor : float, optional
        Absolute floor under which the lower bound never falls, even if a ratio is
        zero or negative (degenerate component). Default 1e-6.

    Returns
    -------
    lower, upper : float, float
        The shared band, always positive.
    """
    ratios = np.maximum(np.abs(np.asarray(ratios, dtype=float)), min_floor)
    log_ratios = np.log(ratios)

    if len(ratios) > 1:
        median = np.median(log_ratios)
        mad = np.median(np.abs(log_ratios - median))
        if mad < 1e-12:
            # all ratios ~identical -- MAD-based band would be zero-width
            lower, upper = np.exp(median) / single_factor, np.exp(median) * single_factor
        else:
            lower, upper = np.exp(median - k * mad), np.exp(median + k * mad)
    else:
        r = ratios[0]
        lower, upper = r / single_factor, r * single_factor

    return max(lower, min_floor), upper
