"""
    LowRank.BoundedLrf.py

    Bounded Low-Rank Factorization (Bounded LRF) for rank-2 components.

    Clips B(q) within a physics-motivated envelope derived from the hard-sphere
    structure factor and redistributes excess to A(q), preserving the row-wise
    intensity sum  A(q)*c1 + B(q)*c2. The envelope is enforced only for
    q >= b1 = pi/R; below b1 the plain rank-2 solution is kept (molass-library#411).

    Ported from molass_legacy BoundedLrfSolver.py (coerce_bounds + estimate_RgL).

    Status (molass-researcher experiments 64-66, 2026-11, simulations with known truth): the hard clip is the hard-threshold form of a bound that
    holds at every q for particles with a hard core (|B/A| <= K min(1, L 3/(q sigma)^2)). Applied as a clip it leaves envelope-sized noise in A(q) at
    high q and had mid-q failures on non-spherical particles and non-hard-sphere interactions (worst mid-q error 146 against 32 for the soft version);
    with the library's own elution curve and unweighted SVD denoising its low-q gain is small (0.057 against 0.125 without correction, 0.013 with the soft
    version, refined curve and whitened denoising). The soft, noise-weighted form of the same bound is :mod:`molass.LowRank.SoftBoundedLrf`
    (``decomposition.set_rank2_method('soft_bounded')``), which is now the default for rank-2 components; this method remains available as
    ``set_rank2_method('bounded')``.
    On the real SAMPLE3 the two give the same Guinier-region correction (nothing is clipped there).
"""
import warnings
import numpy as np
from scipy.optimize import minimize
from bisect import bisect_right
from molass.SAXS.Theory.SolidSphere import phi


BAND_FACTOR = 1.5               # the band is b1 <= q < b2 = BAND_FACTOR * b1
BAND_CLIP_WARN = 0.3            # warn when more than this fraction of the band points is clipped
L_PENALTY_TOL = 0.01            # the stage-1 penalty L >= 2 is "active" when the stage-1 L is within this of 2
Q_MIN_WARN = 0.02               # warn when the lowest q used is above this (1/Angstrom)


class BoundedLrfInfo(dict):
    """Per-component Bounded LRF diagnostic info (molass-library#413).

    A plain ``dict`` subclass -- every existing usage pattern (``info['K']``,
    ``.items()``, ``.get()``, iteration, ``k in info``, ...) keeps working
    exactly as before. The only difference is ``repr()``: printing this
    (e.g. inspecting ``decomp.bounded_lrf_info`` in a notebook) shows only
    the scalar fields and the *shape* of the array fields
    (``bq_bounds``, ``bq_original``, ``bq_coerced``), instead of dumping the
    full arrays -- which can otherwise be hundreds of lines for a single
    component. Index into the fields directly to get the raw arrays.

    Fields
    ------
    K, L, R, Rg : float
        The fitted structure-factor amplitude, the bound-tightness, the sphere-equivalent radius
        ``sqrt(5/3) * Rg`` and the Rg it was derived from (the Rg estimated from the naive rank-2 A(q)).
    bq_bounds, bq_original, bq_coerced : numpy.ndarray
        The envelope (``(-bound, +bound)``, defined at all q, enforced for ``q >= cutoff_q``), B(q) before and after clipping.
    cutoff_q : float
        ``b1 = pi / R``: B(q) is clipped only from here up (#411). It depends on the Rg given to the method.
    band_upper_q : float
        ``b2 = 1.5 * b1``, the upper end of the band ``b1 <= q < b2``.
    clipped_fraction : dict
        Fraction of the points clipped, for ``below_b1`` (0 by construction), ``band`` and ``above_b2``.
    moved_to_A : dict
        RMS of what was moved from B(q) into A(q), ``(B - B_clipped) * c2 / c1``, relative to the RMS of A(q), per region.
    max_move_in_band : float
        Largest ``|(B - B_clipped) * c2 / c1| / |A|`` over the band: how much the clipping changes A(q) relative to A(q) just above the
        cut-off, where A(q) below ``cutoff_q`` is untouched (the "step" of experiment 65 is of this size when the clipping starts at the cut-off).
    L_stage1 : float
        L of the stage-1 fit (``B ~ -K phi(2 L R q) A``); ``L_penalized`` is True when it sits at the penalty bound 2.
    q_min_used : float
        Lowest q of the data given to the method (the trimming decides it and it can be high for strong effects).
    c1 : float
        Peak concentration of the component curve that was used.
    """
    _ARRAY_KEYS = ('bq_bounds', 'bq_original', 'bq_coerced')

    def __repr__(self):
        parts = [f"{k}={self[k]:.4g}" for k in ('K', 'L', 'R', 'Rg', 'cutoff_q', 'max_move_in_band') if k in self]
        if 'clipped_fraction' in self:
            parts.append(f"clipped(band)={self['clipped_fraction']['band']:.0%}")
            parts.append(f"clipped(>=b2)={self['clipped_fraction']['above_b2']:.0%}")
        if 'L_penalized' in self:
            parts.append(f"L_penalized={self['L_penalized']}")
        for k in self._ARRAY_KEYS:
            if k in self:
                v = self[k]
                shape = v[0].shape if isinstance(v, tuple) else v.shape
                parts.append(f"{k}=<array {shape}>")
        return f"BoundedLrfInfo({', '.join(parts)})"

    def findings(self):
        """What deserves a second look, as :class:`molass.LowRank.Findings.Finding` records (code, the library's text, a plain-language text, the part of the
        profile affected, a suggested check, the numbers); the texts of :meth:`warnings_list` are their ``text`` (molass-library#423)."""
        from molass.LowRank.Findings import Finding
        out = []
        cf = self['clipped_fraction']
        if cf['below_b1'] > 0:
            out.append(Finding(
                code='clipped_below_b1',
                text="B(q) was clipped below the cut-off, which should not happen",
                plain="B(q) was clipped below the cut-off pi/R, where the Bounded LRF is meant to leave it alone. This should not happen and is probably a defect.",
                region=f"below the cut-off {self['cutoff_q']:.3g} 1/A",
                check="Report it with the data (the other rank-2 method, set_rank2_method('soft_bounded'), is not affected by this).",
                values=dict(clipped_below_b1=float(cf['below_b1']))))
        if cf['band'] > BAND_CLIP_WARN:
            out.append(Finding(
                code='clipped_band',
                text=f"B(q) exceeds the hard-sphere envelope at {cf['band']:.0%} of the points in the band "
                     f"{self['cutoff_q']:.3g} <= q < {self['band_upper_q']:.3g} (noise or real structure; A(q) changes by up to "
                     f"{self['max_move_in_band']:.1%} there; the cut-off follows Rg = {self['Rg']:.1f} A)",
                plain=f"B(q) is larger than a hard sphere allows at {cf['band']:.0%} of the points at mid q ({self['cutoff_q']:.3g}-{self['band_upper_q']:.3g} 1/A), "
                      f"and the hard clip moves up to {self['max_move_in_band']:.1%} of A(q) there. That is noise or real structure the hard-sphere envelope does not describe.",
                region=f"mid q, {self['cutoff_q']:.3g}-{self['band_upper_q']:.3g} 1/A",
                check="Compare with set_rank2_method('soft_bounded') and with Ranks = 1 (rank2_report shows the Rg of both).",
                values=dict(clipped_band=float(cf['band']), max_move_in_band=float(self['max_move_in_band']), threshold=BAND_CLIP_WARN)))
        if self['L_penalized']:
            out.append(Finding(
                code='l_penalized',
                text="the stage-1 L sits at the penalty bound 2: the envelope does not follow the shape of B(q)",
                plain="The fit of the envelope stopped at its lower limit (L = 2): the envelope does not follow the shape of B(q), so the clip above the cut-off is only approximate.",
                region=f"mid and high q (above {self['cutoff_q']:.3g} 1/A)",
                check="Compare with set_rank2_method('soft_bounded'), which does not fit L.",
                values=dict(L_stage1=float(self['L_stage1']))))
        if self['K'] < 0 or self['L'] < 0:
            out.append(Finding(
                code='kl_negative',
                text=f"K = {self['K']:.3g}, L = {self['L']:.3g}: a negative value means the stage-1 fit did not find the hard-sphere shape of B(q)",
                plain=f"The hard-sphere fit of B(q) gave a negative amplitude or size (K = {self['K']:.2g}, L = {self['L']:.2g}): B(q) does not have the hard-sphere shape, "
                      f"so the envelope is not meaningful.",
                region="all q (the envelope)",
                check="Do not rely on the Bounded LRF here; use set_rank2_method('soft_bounded') or Ranks = 1.",
                values=dict(K=float(self['K']), L=float(self['L']))))
        if self['q_min_used'] > Q_MIN_WARN:
            out.append(Finding(
                code='q_min_high',
                text=f"the lowest q used is {self['q_min_used']:.3g} 1/A (above {Q_MIN_WARN}): the trimming left little of the low-q region the correction acts on",
                plain=f"The lowest q used is {self['q_min_used']:.3g} 1/A: the trimming cut away much of the low-q region where the interparticle effect acts, "
                      f"so the correction has little to work on.",
                region="low q",
                check="Trim less at small angles (small_angle_limit) if the data allow.",
                values=dict(q_min_used=float(self['q_min_used']), threshold=Q_MIN_WARN)))
        return out

    def warnings_list(self):
        """The reasons (strings) why this result deserves a second look; the same texts are emitted as a ``UserWarning``."""
        return [f.text for f in self.findings()]


def clipping_summary(qv, aq, bq, bq_coerced, c1, R):
    """Where and how much ``coerce_bounds`` clipped: ``cutoff_q``, ``band_upper_q``, ``clipped_fraction``, ``moved_to_A``, ``max_move_in_band``
    (see :class:`BoundedLrfInfo`)."""
    b1 = np.pi / R
    b2 = BAND_FACTOR * b1
    regions = {'below_b1': qv < b1, 'band': (qv >= b1) & (qv < b2), 'above_b2': qv >= b2}
    moved = (bq - bq_coerced) * c1                    # (B - B_clipped) * c2 / c1 with c2 = c1**2
    clipped_fraction, moved_to_A = {}, {}
    for name, m in regions.items():
        n = int(m.sum())
        clipped_fraction[name] = float(np.mean(bq[m] != bq_coerced[m])) if n else 0.0
        moved_to_A[name] = float(np.sqrt(np.mean(moved[m] ** 2)) / np.sqrt(np.mean(aq[m] ** 2))) if n else 0.0
    band = regions['band'] & (aq != 0)
    max_move = float(np.max(np.abs(moved[band]) / np.abs(aq[band]))) if band.any() else 0.0
    return dict(cutoff_q=float(b1), band_upper_q=float(b2), clipped_fraction=clipped_fraction, moved_to_A=moved_to_A, max_move_in_band=max_move)


def estimate_KL(qv, aq, bq, Rg, c1, return_stage1_L=False):
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
    return_stage1_L : bool, optional
        Also return the L of Stage 1 (a fourth value), to see whether the penalty ``L >= 2`` is active (#413).

    Returns
    -------
    K : float
        Structure factor amplitude (from Stage 1).
    L : float
        Bound-tightness parameter (from Stage 2).
    R : float
        Sphere-equivalent radius  sqrt(5/3) * Rg.
    L_stage1 : float
        Only if ``return_stage1_L``.
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
        return (hK, hL, R, hL) if return_stage1_L else (hK, hL, R)

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

    return (hK, L, R, hL) if return_stage1_L else (hK, L, R)


def coerce_bounds(qv, aq, bq, c1, L, R):
    """
    Clip B(q) within the physics-motivated envelope and redistribute
    the excess to A(q) so that  A(q)*c1 + B(q)*c2  is preserved row-wise.

    The envelope ``1/(q*L*R)^2`` is the large-x asymptote of the hard-sphere
    function, not a bound below the first boundary ``b1 = pi/R``, and the
    interparticle correction itself lives at low q. Points with ``q < b1`` are
    therefore **not clipped** (B(q) and A(q) stay as the plain rank-2 solution);
    the envelope applies only from ``b1`` up (molass-library#411).

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
        B(q) after clipping (unchanged for q < pi/R).
    bq_bounds : tuple of ndarray
        (-bq_bound, +bq_bound) envelope arrays (defined at all q, enforced for q >= pi/R).
    """
    c2 = c1 ** 2
    bound = 1 / (qv * L * R) ** 2
    bq_bound = bound * aq / c1
    bq_bounds = (-bq_bound, bq_bound)
    clipped = np.clip(bq, -bq_bound, bq_bound)
    bq_coerced = np.where(qv < np.pi / R, bq, clipped)
    aq_corrected = aq + (bq - bq_coerced) * c2 / c1
    return aq_corrected, bq_coerced, bq_bounds


def apply_bounded_lrf(qv, P_full, C_full, ranks, guinier_objects, warn=True):
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
    warn : bool, optional
        Emit a ``UserWarning`` when a component's diagnostics deserve a second look
        (:meth:`BoundedLrfInfo.warnings_list`, molass-library#413).

    Returns
    -------
    P_truncated : ndarray, shape (num_q, num_components)
        Corrected spectral factors (A columns only), ready for downstream use.
    info : dict
        Keyed by component index; each value is a :class:`BoundedLrfInfo`
        (a plain ``dict`` subclass -- all existing ``info[k]['K']``-style
        access keeps working) with fields K, L, R, Rg, bq_bounds,
        bq_original, bq_coerced. Its ``repr()`` is concise (K/L/R/Rg plus
        array shapes only) so printing ``decomp.bounded_lrf_info`` for a
        quick look doesn't dump the full arrays -- index into the fields
        directly (e.g. ``info[k]['bq_coerced']``) to get the raw data.
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

        K, L, R, L_stage1 = estimate_KL(qv, aq, bq, Rg, c1, return_stage1_L=True)
        aq_corrected, bq_coerced, bq_bounds = coerce_bounds(qv, aq, bq, c1, L, R)

        P_out[:, k] = aq_corrected
        P_out[:, b_col] = bq_coerced

        info[k] = BoundedLrfInfo(
            K=K, L=L, R=R, Rg=Rg,
            bq_bounds=bq_bounds,
            bq_original=bq,
            bq_coerced=bq_coerced,
            **clipping_summary(qv, aq, bq, bq_coerced, c1, R),
            L_stage1=float(L_stage1),
            L_penalized=bool(abs(L_stage1 - 2.0) < L_PENALTY_TOL),
            q_min_used=float(np.min(qv)),
            c1=float(c1),
        )
        reasons = info[k].warnings_list()
        if reasons and warn:
            warnings.warn(f"Bounded LRF, component {k}: " + "; ".join(reasons) + " (see decomposition.bounded_lrf_info)", UserWarning, stacklevel=2)

    P_truncated = P_out[:, :num_components]
    return P_truncated, info
