"""
    LowRank.BoundedLrf.py

    Bounded Low-Rank Factorization (Bounded LRF) for rank-2 components.

    Clips B(q) within a physics-motivated envelope derived from the hard-sphere
    structure factor and redistributes excess to A(q), preserving the row-wise
    intensity sum  A(q)*c1 + B(q)*c2.

    Ported from molass_legacy BoundedLrfSolver.py (coerce_bounds + estimate_RgL).
"""
import numpy as np
from scipy.optimize import minimize
from bisect import bisect_right
from molass.SAXS.Theory.SolidSphere import phi


def estimate_KL(qv, aq, bq, Rg, c1):
    """
    Estimate the hard-sphere model parameters K and L.

    Stage 1: fit K, L by matching B(q) to  -K * phi(2*L*R*q) * A(q)
    Stage 2: refine L so that the envelope  A(q)/(c1*(q*L*R)^2)  tightly
             covers the data without excessive violations.

    Parameters
    ----------
    qv : ndarray
        q-vector.
    aq : ndarray
        A(q) column from the naïve factorization.
    bq : ndarray
        B(q) column from the naïve factorization.
    Rg : float
        Radius of gyration from Guinier analysis.
    c1 : float
        Peak monomer concentration.

    Returns
    -------
    K : float
        Structure factor amplitude (from Stage 1).
    L : float
        Bound-tightness parameter (from Stage 2).
    R : float
        Sphere-equivalent radius  sqrt(5/3) * Rg.
    """
    R = np.sqrt(5 / 3) * Rg

    # --- Stage 1 ---
    i1 = bisect_right(qv, 0.01)
    i2 = bisect_right(qv, 0.2)
    sl = slice(i1, i2)
    qv_ = qv[sl]
    aq_ = aq[sl]
    bq_ = bq[sl]

    def objective1(p):
        K_, L_ = p
        h_bq = -K_ * phi(qv_, 2 * L_ * R) * aq_
        penalty = min(0, K_) ** 2 + min(0, L_ - 2) ** 2
        return np.mean((h_bq - bq_) ** 2) + penalty

    ret = minimize(objective1, (0.3, 1.0))
    hK, hL = ret.x

    # --- Stage 2 ---
    kernel = np.hanning(5)
    kernel /= kernel.sum()
    smoothed = np.convolve(bq_, kernel, mode='same')
    j2 = i1 + np.argmax(smoothed)
    sl2 = slice(j2, i2)
    q2 = qv[sl2]
    aq2 = aq[sl2]
    bq2 = bq[sl2]

    if len(q2) < 3:
        return hK, hL, R

    h_bq2 = -hK * phi(q2, 2 * hL * R) * aq2 / c1
    upper_bq = np.maximum(bq2, h_bq2)

    def objective2(p):
        (L_,) = p
        bound = aq2 / (c1 * (q2 * L_ * R) ** 2)
        diff = upper_bq - bound
        pos = diff[diff > 0]
        neg = diff[diff <= 0]
        cost = 0.0
        if len(pos) > 0:
            cost += 99 * np.mean(pos ** 2)
        if len(neg) > 0:
            cost += np.mean(neg ** 2)
        return cost

    ret2 = minimize(objective2, (hL,))
    L = ret2.x[0]

    return hK, L, R


def coerce_bounds(qv, aq, bq, c1, L, R):
    """
    Clip B(q) within the physics-motivated envelope and redistribute
    the excess to A(q) so that  A(q)*c1 + B(q)*c2  is preserved row-wise.

    Parameters
    ----------
    qv : ndarray
        q-vector.
    aq : ndarray
        A(q) column.
    bq : ndarray
        B(q) column.
    c1 : float
        Peak monomer concentration.
    L : float
        Bound-tightness parameter from estimate_KL.
    R : float
        Sphere-equivalent radius.

    Returns
    -------
    aq_corrected : ndarray
        A(q) after redistribution.
    bq_coerced : ndarray
        B(q) after clipping.
    bq_bounds : tuple of ndarray
        (-bq_bound, +bq_bound) envelope arrays.
    """
    c2 = c1 ** 2
    bound = 1 / (qv * L * R) ** 2
    bq_bound = bound * aq / c1
    bq_bounds = (-bq_bound, bq_bound)
    bq_coerced = np.clip(bq, -bq_bound, bq_bound)
    aq_corrected = aq + (bq - bq_coerced) * c2 / c1
    return aq_corrected, bq_coerced, bq_bounds


def apply_bounded_lrf(qv, P_full, C_full, ranks, guinier_objects):
    """
    Apply Bounded LRF to every rank-2 component in P_full.

    Parameters
    ----------
    qv : ndarray
        q-vector.
    P_full : ndarray, shape (num_q, total_rank)
        Full spectral factor matrix including B(q) columns.
    C_full : ndarray, shape (total_rank, num_frames)
        Full concentration matrix including c^2 rows.
    ranks : list of int
        Rank for each component (1 or 2).
    guinier_objects : list
        Pre-computed RgEstimator objects (one per component).

    Returns
    -------
    P_truncated : ndarray, shape (num_q, num_components)
        Corrected spectral factors (A columns only), ready for downstream use.
    info : dict
        Keyed by component index; each value is a dict with diagnostic fields
        K, L, R, Rg, bq_bounds, bq_original, bq_coerced.
    """
    num_components = len(ranks)
    P_out = P_full.copy()
    info = {}

    extra_col = num_components
    for k, r in enumerate(ranks):
        if r != 2:
            continue
        b_col = extra_col
        extra_col += 1

        aq = P_full[:, k].copy()
        bq = P_full[:, b_col].copy()

        Rg = guinier_objects[k].Rg
        if Rg is None or Rg <= 0:
            continue

        j_peak = np.argmax(C_full[k, :])
        c1 = C_full[k, j_peak]

        K, L, R = estimate_KL(qv, aq, bq, Rg, c1)
        aq_corrected, bq_coerced, bq_bounds = coerce_bounds(qv, aq, bq, c1, L, R)

        P_out[:, k] = aq_corrected
        P_out[:, b_col] = bq_coerced

        info[k] = {
            'K': K, 'L': L, 'R': R, 'Rg': Rg,
            'bq_bounds': bq_bounds,
            'bq_original': bq,
            'bq_coerced': bq_coerced,
        }

    P_truncated = P_out[:, :num_components]
    return P_truncated, info
