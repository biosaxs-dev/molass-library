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


# ---------------------------------------------------------------------------
# Model-agnostic SEC_conformance (molass-library/molass-legacy#289)
# ---------------------------------------------------------------------------
#
# Earlier, SEC_conformance (one of the 7 scores synthesized into the rigorous-
# optimization Score Value) was computed per elution model from model-specific
# column parameters (e.g. EGH's single-pore theory needed Rg + pore size).
# Every model but EGH either stubbed this to a constant or special-cased it,
# making cross-model SV comparisons unfair -- see
# molass-researcher/experiments/46_sec_conformance_fairness for the full
# derivation and an empirical measurement of the resulting bias.
#
# This replaces that per-model logic with one formula that needs only the
# post-decomposition *moments* of each component's elution curve (tR = mean,
# sigma = sqrt(variance) -- see molass_legacy.Peaks.MomentsUtils.compute_moments),
# which every model produces identically regardless of its internal physics.

SECCONF_LOWER_BOUND = -2.5
# Intentionally duplicated from molass_legacy.SecTheory.ColumnConstants rather
# than imported: molass-legacy depends on molass-library, not the reverse.
BAD_CONFORMANCE_REDUCE = 1e-2
SEC_PENALTY_SCALE = 1e8
NEUTRAL_RAW_CONFORMANCE = 0.0


def conformance_score(tR, sigma):
    """Model-agnostic SEC_conformance (raw; the caller applies its own final-scale
    transform, e.g. BasicOptimizer.compute_comformance's ``*0.5 - 0.1``).

    Fits the shared Martin-Synge plate-theory relation ``tR_i = tI + sqrt(N)*sigma_i``
    to the given per-component moments via ordinary least squares, and scores the
    residual on the same log-scale/floor structure historically used by EGH's
    single-pore-theory ``sec_comformance`` -- but using only ``(tR, sigma)``, so it
    applies identically to every elution model (no Rg, no pore size, no
    model-specific column parameters needed).

    Parameters
    ----------
    tR : array-like
        Per-component retention times (first raw moment of each component's
        elution curve).
    sigma : array-like
        Per-component widths (sqrt of the second central moment).

    Returns
    -------
    float
        ``NEUTRAL_RAW_CONFORMANCE`` when fewer than 2 components (no regression
        is possible with a single point -- neither rewarded nor penalized).
        Otherwise a log-scaled residual, floored at ``SECCONF_LOWER_BOUND``
        (best) and reduced (via ``BAD_CONFORMANCE_REDUCE``) when it would
        otherwise be positive (worst), mirroring the historical EGH formula's
        scale so synthesize()'s score weighting stays calibrated.
    """
    tR = np.asarray(tR, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    if len(tR) < 2:
        return NEUTRAL_RAW_CONFORMANCE

    slope, intercept = np.polyfit(sigma, tR, 1)   # slope = sqrt(N), intercept = tI
    model_tR = intercept + slope * sigma
    residual = float(np.average((model_tR - tR) ** 2))

    # Physical-validity penalty: width must grow with retention (slope > 0),
    # injection must precede every component's elution (intercept < min(tR)),
    # and the implied plate count must stay within the same sanity bounds
    # already used to seed EGH (N_LOWER_BOUND/N_UPPER_BOUND above).
    N = slope ** 2
    violation = (
        min(0.0, slope) ** 2
        + max(0.0, intercept - np.min(tR)) ** 2
        + (min(0.0, N - N_LOWER_BOUND) / N_LOWER_BOUND) ** 2
        + (max(0.0, N - N_UPPER_BOUND) / N_UPPER_BOUND) ** 2
    )

    total = residual + SEC_PENALTY_SCALE * violation
    log_conformance = np.log10(total) if total > 0 else SECCONF_LOWER_BOUND
    if log_conformance > 0:
        log_conformance *= BAD_CONFORMANCE_REDUCE   # large conformance at early stages can be misleading
    return max(SECCONF_LOWER_BOUND, log_conformance)
