"""
SEC.Models.MartinSynge.py

Martin-Synge plate theory (1941): a chromatographic column behaves as a cascade
of N equilibrium stages ("theoretical plates"), which is why elution peaks are
Gaussian and why their width is not a free quantity -- it is fixed by the
retention time itself:

    N = ((tR - tI) / sigma)**2      i.e.      sigma = (tR - tI) / sqrt(N)

tR here is the same quantity molass.SEC.Models.Simple.egh's own signature calls
tR (the peak-center parameter, on the raw acquisition axis) -- deliberately
unified to that one name rather than introducing a second alias (e.g. "mu")
for it. (tR - tI) is the injection-corrected retention time; it is written out
explicitly wherever needed rather than given its own symbol.

Equivalent to the standard tangent-line/base-width method (N = 16(tR/W)**2 with
W=4*sigma for a Gaussian) -- NOT the half-height (5.54 coefficient) or EMG
(tailing-inclusive) conventions, since sigma here is the EGH's Gaussian
component alone, deliberately excluding tau (tailing). Different real-peak
measurement conventions diverge once tailing is present; this module always
uses the sigma-only (tangent-line-equivalent) definition of N.

tI here is *not* the physical dead/void time used elsewhere in this codebase
(e.g. SDM's t0, the mean mobile-phase transit time -- a real column property).
It is purely a data-acquisition bookkeeping offset: tR is measured on the raw
frame axis, timestamped from an arbitrary acquisition start rather than from
the injection event, so tI is the (estimated) injection instant on that same
axis. Once subtracted, (tR - tI) is exactly the plain, unadjusted retention
time the standard N formula above uses -- no further void-time correction is
implied or needed.

tI and N are properties of the column and flow rate, not of the eluting
species, so a single (tI, N) pair applies to every component in one run.
Neither is directly measured -- see above -- so both must be estimated from
the mutual consistency of the observed (tR_i, sigma_i) pairs across components.

This module is the shared home for that estimation, used by both EGH-fitting
paths (Decompose.Proportional, LowRank.CurveDecomposer) so that the EGH seed --
which every column model (SDM/LKM/EDM/GRM) is later upgraded from -- respects
this relation before any asymmetry (tau) or column-specific physics is added.
tau itself is a secondary modification layered on this Gaussian core, not a
co-equal width parameter (see TAU_BOUND_RATIO in Decompose.Proportional).
"""
import numpy as np

# 48000 plates/m * 0.3m (30cm column); see molass_legacy.SecTheory.ColumnConstants
DEFAULT_NUM_PLATES = 14400
N_LOWER_BOUND = 100.0
N_UPPER_BOUND = 1.0e6


def estimate_tI_N(tR, sigma, num_plates=None):
    """
    Estimate the shared injection time tI and plate count N from per-component
    (tR, sigma) pairs, via tR_i = tI + sqrt(N)*sigma_i (linear regression).

    This is only a seed for the joint optimizer, never the final answer. Falls
    back to a fixed, physically generic N when there are too few components to
    regress (<2), the fitted slope is non-positive (width would not grow with
    retention -- inconsistent with the theory), or the fitted tI is not below
    every component's retention time (injection cannot follow elution).

    Parameters
    ----------
    tR : array-like
        Per-component retention times (naive independent EGH fit; same tR as
        molass.SEC.Models.Simple.egh's own parameter).
    sigma : array-like
        Per-component Gaussian widths (naive independent EGH fit).
    num_plates : float, optional
        Fallback plate count. Default DEFAULT_NUM_PLATES=14400.

    Returns
    -------
    tI, N : float
        Initial guess for the shared injection time and plate count.
    """
    tR = np.asarray(tR, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    N_fallback = num_plates if num_plates is not None else DEFAULT_NUM_PLATES
    tI_lo, tI_hi = tI_bounds(tR)
    tI_fallback = tI_hi

    if len(tR) < 2:
        tI, N = tI_fallback, N_fallback
    else:
        slope, intercept = np.polyfit(sigma, tR, 1)
        if slope <= 0 or intercept >= np.min(tR):
            tI, N = tI_fallback, N_fallback
        else:
            tI, N = intercept, slope**2

    # keep the seed within the same bounds the joint optimizer will use (see tI_bounds,
    # N_LOWER_BOUND/N_UPPER_BOUND) -- a seed just outside them is otherwise possible when
    # the regression/fallback formulas don't perfectly agree with the bound heuristics.
    tI = min(max(tI, tI_lo), tI_hi)
    N = min(max(N, N_LOWER_BOUND), N_UPPER_BOUND)
    return tI, N


def compute_sigma(tR, tI, N):
    """
    Derive the Gaussian width from the shared plate-theory parameters:
    sigma = (tR - tI) / sqrt(N). Sigma is an output of (tI, N, tR), not an
    independently-fit quantity.

    Parameters
    ----------
    tR : float or array-like
        Retention time(s) (same tR as molass.SEC.Models.Simple.egh's own
        parameter -- not yet injection-corrected).
    tI : float
        Shared injection time.
    N : float
        Shared plate count.

    Returns
    -------
    float or array-like
        The derived Gaussian width(s).
    """
    return (np.asarray(tR, dtype=float) - tI) / np.sqrt(N)


def tI_bounds(tR):
    """
    Bounds for the shared injection time tI.

    Upper: must precede every component's retention time (physical necessity),
    with a small margin so the earliest component's sigma cannot be forced to
    (near) zero. Lower: generous, scaled to the retention-time spread, since
    there is no physical basis to constrain it further.

    Parameters
    ----------
    tR : array-like
        Per-component retention times.

    Returns
    -------
    (lower, upper) : tuple of float
    """
    tR = np.asarray(tR, dtype=float)
    span = max(np.max(tR) - np.min(tR), 1.0) if len(tR) > 1 else max(abs(np.min(tR)), 1.0)
    upper = np.min(tR) - 0.05 * span
    lower = np.min(tR) - 10 * span
    return lower, upper
