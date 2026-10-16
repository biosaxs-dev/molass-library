"""
Decompose.RgOrder.py

Rg-order penalty for the quick proportional decomposition (molass-library#295).

SEC elutes larger particles first, so the component Rgs obtained from the LRF should decrease
with elution order. The rigorous objective already penalizes violations; the quick proportional
fit only sees the 1-D elution curve and therefore can land on component curves whose LRF
scattering profiles are not SEC-ordered (and which change drastically under tiny perturbations).

This module provides a cheap, per-trial-curve Rg proxy so the same kind of penalty can be
added to the quick objective. The real Guinier fit (``RgEstimator``) is far too slow for an
inner optimizer loop, so the proxy uses the low-q decay of each component's scattering profile.
"""
import numpy as np

DEFAULT_RG_ORDER_WEIGHT = 0.1
# same soft tolerance (in Angstrom) as molass_legacy BasicOptimizer.RG_ORDER_TOLERANCE
RG_ORDER_TOLERANCE = 2.0
RG_ORDER_PENALTY_SCALE = 1e3
# Guinier validity limit q*Rg <= GUINIER_QRG_LIMIT for the reference Rg fit
GUINIER_QRG_LIMIT = 1.3
# the proxy compares the low-q intensity with the intensity near q_hi = PROXY_QRG_LIMIT / Rg_ref;
# a somewhat wider window than the Guinier limit gives it enough sensitivity (tuned on Y17AH20N)
PROXY_QRG_LIMIT = 1.6
NUM_LOW_POINTS = 4
MIN_HIGH_POINTS = 3
MIN_WINDOW_POINTS = 8
VERY_SMALL_VALUE = 1e-10


def estimate_reference_rg(qv, intensity, num_iterations=5):
    """Rough Guinier Rg of a single profile (iteratively adapting the q window).

    Returns None if no positive-slope-free Guinier fit is possible.
    """
    qv = np.asarray(qv, dtype=float)
    intensity = np.asarray(intensity, dtype=float)
    n = min(MIN_WINDOW_POINTS + 2, len(qv))
    rg = None
    for _ in range(num_iterations):
        q, y = qv[:n], intensity[:n]
        if np.any(y <= 0) or len(q) < 3:
            return rg
        slope = np.polyfit(q ** 2, np.log(y), 1)[0]
        if slope >= 0:
            return rg
        rg = np.sqrt(-3 * slope)
        n_new = int(np.searchsorted(qv, GUINIER_QRG_LIMIT / rg, side='right'))
        n = max(MIN_WINDOW_POINTS, min(n_new, len(qv)))
    return rg


class RgOrderPenalty:
    """Callable returning the (unweighted) squared Rg-order violation of trial elution curves.

    Parameters
    ----------
    M : ndarray, shape (n_q, n_frames)
        XR data matrix (the same frames as the elution curves being fitted).
    qv : ndarray, shape (n_q,)
        q values in 1/Angstrom.
    num_components : int
        Number of components (rank of the denoised matrix).
    weight : float
        Weight of ``log10(1 + scale * violation)`` in the quick objective.
    """

    def __init__(self, M, qv, num_components, weight=DEFAULT_RG_ORDER_WEIGHT):
        self.weight = weight
        self.enabled = False
        M = np.asarray(M, dtype=float)
        qv = np.asarray(qv, dtype=float)
        if weight <= 0 or num_components < 2 or M.ndim != 2 or M.shape[0] != len(qv):
            return
        if len(qv) < NUM_LOW_POINTS + MIN_HIGH_POINTS + 1:
            return

        from molass.LowRank.LowRankInfo import get_denoised_data
        M_ = get_denoised_data(M, rank=num_components)
        # reference Rg from the mean profile, which is dominated by the major (largest) species
        rg_ref = estimate_reference_rg(qv, M_.mean(axis=1))
        if rg_ref is None or not np.isfinite(rg_ref):
            return

        q_hi = PROXY_QRG_LIMIT / rg_ref
        lo = np.arange(NUM_LOW_POINTS)
        hi = np.where((qv >= 0.85 * q_hi) & (qv <= q_hi))[0]
        hi = hi[hi > NUM_LOW_POINTS]
        if len(hi) < MIN_HIGH_POINTS:
            # coarse q grid: use the MIN_HIGH_POINTS points ending at q_hi instead
            k = min(int(np.searchsorted(qv, q_hi)), len(qv) - 1)
            hi = np.arange(k - MIN_HIGH_POINTS + 1, k + 1)
            if hi[0] <= NUM_LOW_POINTS:
                return
        self._rows = np.concatenate([lo, hi])
        self._n_lo = len(lo)
        self._M_sel = M_[self._rows, :]
        self._q2_lo = np.mean(qv[lo] ** 2)
        self._q2_hi = np.mean(qv[hi] ** 2)
        if self._q2_hi <= self._q2_lo:
            return
        self.rg_ref = rg_ref
        self.enabled = True

    def rg_proxy(self, cy_list):
        """Rg proxy of each component from the trial elution curves (None on failure)."""
        try:
            P = self._M_sel @ np.linalg.pinv(np.asarray(cy_list))
        except np.linalg.LinAlgError:
            return None
        lo = P[:self._n_lo].mean(axis=0)
        hi = P[self._n_lo:].mean(axis=0)
        ratio = np.where(lo > 0, hi / np.where(lo > 0, lo, 1.0), 0.0)
        ratio = np.clip(ratio, 1e-3, 1.0)
        return np.sqrt(-3 * np.log(ratio) / (self._q2_hi - self._q2_lo))

    def violation(self, cy_list):
        """Sum of squared SEC-order violations (Rg should decrease with component index)."""
        rg = self.rg_proxy(cy_list)
        if rg is None:
            return 1e6
        diffs = rg[:-1] - rg[1:]
        return float(np.sum(np.minimum(0, diffs + RG_ORDER_TOLERANCE) ** 2))

    def term(self, cy_list):
        """Penalty term to add to the quick objective (0 if disabled)."""
        if not self.enabled:
            return 0.0
        v = self.violation(cy_list)
        return self.weight * np.log10(max(1 + RG_ORDER_PENALTY_SCALE * v, VERY_SMALL_VALUE))
