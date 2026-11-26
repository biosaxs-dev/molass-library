"""
    LowRank.EnvelopePrior.py

    Envelope-prior LRF (EP-LRF): the Bounded LRF's envelope used as a prior instead of a clip
    (molass-researcher experiments 65-66; notebook ``66d_envelope_prior``).

    **The bound.** To first order in the concentration, B(q)/A(q) = beta(q) n f(q), with f the Fourier transform of the Mayer function
    exp(-V(r)/kT) - 1 and beta(q) = <F>^2/<F^2> <= 1 for non-spherical particles. If the particles have a hard core of diameter sigma, f jumps at
    contact and integration by parts gives ``|f(q)| <= (4 pi / q^2) (sigma |jump| + ||h||_1)`` with ``h`` the smooth part of ``(r f)'``: whatever the soft
    part of the potential does, ``|B/A| <= K min(1, L 3 / (q sigma)^2)`` at every q (K: the low-q plateau; L about 2 covers the first S(q) peak and the c^3
    terms). It fails for an adhesive shell (decay 1/q) and for particles without a hard core (polymers, soft particles).

    **The estimator.** Per q the simple LRF (``M ~ A c + B c^2``, weights 1/E^2) gives ``r_hat = B/A`` with its propagated error ``s_r``. With the prior
    ``r ~ N(0, tau^2)``, ``tau(q) = K min(1, L 3 / (q sigma)^2)``, the posterior mean is ``r_hat tau^2 / (tau^2 + s_r^2)``: the plain quadratic correction
    where the data are sharper than the prior (low q), about 0 where the prior is sharper (high q), a blend by the noise between. No switch point, no
    shape model of B(q), no sign constraint. A(q) is then solved with ``B/A = r_post`` fixed. K is the largest significant sliding-window mean of ``|r_hat|`` over the rows with q below ``k_window[1]`` (default 0.035; see :func:`estimate_envelope_K`),
    ``sigma = 2 sqrt(5/3) Rg`` with the Guinier Rg of the corrected profile of the first pass.

    **Concentration curve.** The curve ``c`` is the dominant error of every c^2 correction (K = 1.0 simulation: low-q error 0.215 with the library's XR curve, 0.006
    with the true curve), so by default the curve is refined first (:mod:`molass.LowRank.ConcentrationRefine`) and the matrix is denoised with a whitened SVD
    (:func:`molass.LowRank.LowRankInfo.get_weighted_denoised_data`).

    **Evidence and limits.** On 14 simulated cases (Pedersen shapes x hard-sphere, sticky, Yukawa and RPA interactions, stated noise) it was the only candidate without
    a catastrophic case (worst mid-q error 31 against 91-498), but with the true c it is not more accurate than the plain simple LRF at mid q (robustness, not
    accuracy); an adhesive shell beyond q about 0.08 is not corrected; strong effects (S - 1 = -0.5 at the peak) keep a truncation floor of 0.045-0.06 for every c^2 method.
    Validated on simulations only; real data other than SAMPLE3 were not used.

    **Diagnostics.** ``violation_fraction`` (the share of the band pi/R - 1.5 pi/R where the plain-fit ratio exceeds twice the envelope significantly) in 14 simulated
    cases (2 seeds each): 0.00-0.33 for hard spheres (Percus-Yevick, also anisotropic: 0.00), 0.09-0.54 for the sticky and Yukawa spheres, 1.00 for the cylinder
    with RPA, the Gaussian chain with RPA and the ellipsoid with a Yukawa tail; the warning threshold 0.4 is provisional
    (molass-researcher ``experiments/66_interaction_models/frozen_66e_violation.json``). A high value says the data are not described by a hard-core bound
    (adhesive or soft particles); it does not mean the result is wrong (the rods and the chain were corrected well at low and mid q).
"""
import warnings
import numpy as np

L_DEFAULT = 2.0
K_WINDOW = (0.0, 0.035)          # K is searched among the rows with q below the upper end (the effect can sit below 0.018: real SAMPLE3)
K_ROWS = 5                      # rows of the sliding window of the K estimate
K_SIGNIF = 3.0                  # a window counts only if |mean B/A| > K_SIGNIF standard errors
Q_MIN_WARN = 0.02               # warn when the lowest q used is above this (1/Angstrom)
K_MIN_WARN = 0.05               # K below this: no detectable interparticle term
BAND_FACTOR = 1.5               # the band b1 <= q < BAND_FACTOR b1 (b1 = pi/R) where the envelope violation is judged
VIOLATION_WARN = 0.4            # warn when more than this fraction of the band points exceeds twice the envelope significantly (provisional)


class EnvelopePriorInfo(dict):
    """Per-component EP-LRF diagnostic info (a ``dict``; the ``repr`` shows the scalars and the array shapes only).

    Fields: ``K``, ``sigma``, ``L``, ``rg_seed`` (the Rg of the first pass), ``cutoff_q`` (``pi / R``: where the envelope starts to decay),
    ``r_hat``, ``s_r``, ``tau``, ``r_post`` (arrays over q: the plain-fit ratio B/A, its error, the prior width, the posterior ratio actually used),
    ``weight_mid`` (the mean weight ``tau^2 / (tau^2 + s_r^2)`` over the mid region 1.5 <= q Rg <= 3.5: 1 = all data, 0 = all prior),
    ``violation_fraction`` (the share of the band ``cutoff_q <= q < 1.5 cutoff_q`` where ``|r_hat| - 2 s_r > 2 tau``: the data exceed the hard-core envelope
    significantly, e.g. adhesive or soft particles; above the band the ratio of two small numbers is not reliable), ``c_refined`` (the refined concentration at peak 1 or ``None``), ``c_scale`` (the peak of the library's
    curve; the refined curve in its units is ``c_refined * c_scale``), ``refine`` (the dict of the refinement without the curve) and ``q_min_used``.
    """
    _ARRAY_KEYS = ('r_hat', 's_r', 'tau', 'r_post', 'c_refined')

    def __repr__(self):
        parts = [f"{k}={self[k]:.4g}" for k in ('K', 'sigma', 'L', 'rg_seed', 'cutoff_q', 'weight_mid', 'violation_fraction') if k in self]
        for k in self._ARRAY_KEYS:
            if k in self and self[k] is not None:
                parts.append(f"{k}=<array {np.shape(self[k])}>")
        return f"EnvelopePriorInfo({', '.join(parts)})"

    def warnings_list(self):
        """The reasons (strings) why this result deserves a second look; the same texts are emitted as a ``UserWarning``."""
        out = []
        ref = self.get('refine')
        if ref is not None and ref.get('at_bound'):
            out.append("the concentration refinement ended at a bound of its (hard-sphere) parameters: the effect is not hard-sphere-like or very weak; the refined curve may be unreliable")
        if self['K'] < K_MIN_WARN:
            out.append(f"K = {self['K']:.3g} is small: no detectable interparticle term below q = {K_WINDOW[1]}; rank 2 may not be needed")
        if self['violation_fraction'] > VIOLATION_WARN:
            out.append(f"B/A exceeds twice the hard-core envelope significantly at {self['violation_fraction']:.0%} of the points in the band {self['cutoff_q']:.3g} <= q < {BAND_FACTOR * self['cutoff_q']:.3g}: "
                       f"adhesive or soft particles? the envelope prior then removes real B(q)")
        if self['q_min_used'] > Q_MIN_WARN:
            out.append(f"the lowest q used is {self['q_min_used']:.3g} 1/A (above {Q_MIN_WARN}): the trimming left little of the low-q region the correction acts on")
        return out


def simple_lrf_with_errors(M, E, c):
    """Per q weighted LS of ``M ~ A c + B c^2`` (weights 1/E^2): ``(A, B, var A, var B, cov AB)`` over q."""
    W = 1.0 / E ** 2
    c1, c2 = c, c ** 2
    s11 = np.sum(W * c1 ** 2, axis=1)
    s12 = np.sum(W * c1 * c2, axis=1)
    s22 = np.sum(W * c2 ** 2, axis=1)
    r1 = np.sum(W * M * c1, axis=1)
    r2 = np.sum(W * M * c2, axis=1)
    det = s11 * s22 - s12 ** 2
    A = (s22 * r1 - s12 * r2) / det
    B = (s11 * r2 - s12 * r1) / det
    return A, B, s22 / det, s11 / det, -s12 / det


def estimate_envelope_K(qv, r_hat, s_r, k_window=K_WINDOW, rule="peak"):
    """The plateau K of the envelope from the plain-fit ratio ``r_hat = B/A`` and its error ``s_r``.

    ``rule='peak'`` (default): the largest ``|mean r_hat|`` of a sliding window of ``K_ROWS`` consecutive rows (precision-weighted, rows with q below the upper end of
    ``k_window`` and above its lower end), among the windows whose mean is significant (``K_SIGNIF`` standard errors). The effect can sit at the lowest q:
    on the real SAMPLE3 B/A is -0.31 at q = 0.0075-0.010 and about +0.04 at 0.018-0.035; the mean over 0.018-0.035 (``rule='mean'``, the first version) is 0.04
    and removes the effect. If no window is significant, the mean ``|r_hat|`` over the window is used.
    """
    qv = np.asarray(qv, float)
    ok = np.isfinite(r_hat) & np.isfinite(s_r) & (s_r > 0)
    sel = np.flatnonzero((qv >= k_window[0]) & (qv < k_window[1]) & ok)
    if rule == "mean":
        sel_m = sel[qv[sel] >= 0.018] if (qv[sel] >= 0.018).sum() >= 3 else sel
        return float(np.mean(np.abs(r_hat[sel_m]))) if len(sel_m) else 0.0
    best = 0.0
    for i in range(0, max(0, len(sel) - K_ROWS + 1)):
        w = sel[i:i + K_ROWS]
        if w[-1] - w[0] != K_ROWS - 1:
            continue                                     # not consecutive rows
        wt = 1.0 / s_r[w] ** 2
        mean = float(np.sum(wt * r_hat[w]) / np.sum(wt))
        se = float(1.0 / np.sqrt(np.sum(wt)))
        if abs(mean) > K_SIGNIF * se:
            best = max(best, abs(mean))
    if best == 0.0 and len(sel):
        best = float(np.mean(np.abs(r_hat[sel[qv[sel] >= 0.018]]))) if (qv[sel] >= 0.018).any() else float(np.mean(np.abs(r_hat[sel])))
    return best


def envelope_prior_lrf(qv, M, M_denoised, E, c, rg_seed, L=L_DEFAULT, k_window=K_WINDOW, k_rule="peak"):
    """EP-LRF for one component on arrays.

    Parameters
    ----------
    qv : array, shape (n_q,)
    M : array, shape (n_q, n_frames)
        The matrix of the component (measured; other components removed). Used for the plain c^2 fit and its errors.
    M_denoised : array, shape (n_q, n_frames)
        The (whitened) rank-2 denoised matrix; A(q) is solved on it.
    E : array, shape (n_q, n_frames)
    c : array, shape (n_frames,)
        The concentration curve **at peak 1**.
    rg_seed : float
        Rg for ``sigma = 2 sqrt(5/3) Rg``.
    L, k_window, k_rule : float, (float, float), str
        ``k_window``: the q range in which K is searched; ``k_rule``: ``'peak'`` or ``'mean'`` (see :func:`estimate_envelope_K`).

    Returns
    -------
    dict
        ``A`` (at peak-1 scale of c), ``r_hat``, ``r_post``, ``tau``, ``s_r``, ``K``, ``sigma``.
    """
    A_s, B_s, vA, vB, cov = simple_lrf_with_errors(M, E, c)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_hat = B_s / A_s
        s_r = np.sqrt(np.maximum(vB / A_s ** 2 + B_s ** 2 * vA / A_s ** 4 - 2 * B_s * cov / A_s ** 3, 1e-30))
    K = estimate_envelope_K(qv, r_hat, s_r, k_window, k_rule)
    sigma = 2 * np.sqrt(5 / 3) * rg_seed
    with np.errstate(divide="ignore", invalid="ignore"):
        tau = K * np.minimum(1.0, L * 3.0 / (qv * sigma) ** 2)
    w = tau ** 2 / (tau ** 2 + s_r ** 2)
    r_post = np.where(np.isfinite(r_hat) & np.isfinite(w), r_hat * w, 0.0)
    W = 1.0 / E ** 2
    h = c[None, :] + r_post[:, None] * (c ** 2)[None, :]
    A = np.sum(W * M_denoised * h, axis=1) / np.sum(W * h * h, axis=1)
    return dict(A=A, r_hat=r_hat, r_post=r_post, tau=tau, s_r=s_r, K=K, sigma=float(sigma))


def apply_envelope_prior_lrf(qv, M, E, C_full, P_full, ranks, seed_objects, refine_c=True, L=L_DEFAULT, k_window=K_WINDOW, k_rule="peak", warn=True):
    """Apply EP-LRF to every rank-2 component (the counterpart of :func:`molass.LowRank.BoundedLrf.apply_bounded_lrf`).

    Parameters
    ----------
    qv : ndarray, shape (n_q,)
    M : ndarray, shape (n_q, n_frames)
        The measured matrix ``xr.M``.
    E : ndarray, shape (n_q, n_frames)
        The stated error ``xr.E`` (required).
    C_full : ndarray, shape (total_rank, n_frames)
        The elution curves including the c^2 rows (as in :func:`apply_bounded_lrf`).
    P_full : ndarray, shape (n_q, total_rank)
        The naive factorization ``M_ pinv(C_full)``, used to remove the other components from ``M`` in multi-component decompositions.
    ranks : list of int
    seed_objects : list
        Pre-computed RgEstimator objects (one per component) from the naive P; their Rg gives the start of the refinement range.
    refine_c : bool
        Refine the concentration curve first (default). ``False`` uses the library's curve.
    L, k_window, k_rule : see :func:`envelope_prior_lrf`.
    warn : bool

    Returns
    -------
    P_truncated : ndarray, shape (n_q, num_components)
        The corrected A columns (in the units of the library's component curve ``C_full[k]``: ``M ~ A C_full[k]``).
    info : dict
        Keyed by component index; each value an :class:`EnvelopePriorInfo`.
    """
    from molass.Guinier.RgEstimator import RgEstimator
    from molass.LowRank.ErrorPropagate import compute_propagated_error
    from molass.LowRank.LowRankInfo import get_weighted_denoised_data
    from molass.LowRank.ConcentrationRefine import refine_concentration
    if E is None:
        raise ValueError("the envelope-prior LRF needs the stated error (xr.E is None)")
    qv = np.asarray(qv, float)
    M = np.asarray(M, float)
    E = np.asarray(E, float)
    num_components = len(ranks)
    P_out = P_full.copy()
    info = {}
    extra_col = num_components
    for k, r in enumerate(ranks):
        if r != 2:
            continue
        b_col = extra_col
        extra_col += 1
        rg0 = seed_objects[k].Rg
        if rg0 is None or not np.isfinite(rg0) or rg0 <= 0:
            continue
        Mk = M.copy()
        for col in range(P_full.shape[1]):
            if col != k and col != b_col:
                Mk = Mk - np.outer(P_full[:, col], C_full[col])
        c0 = np.asarray(C_full[k], float)
        scale = float(np.max(c0))
        Md2 = get_weighted_denoised_data(Mk, E, 2)
        refine_info, c_ref = None, c0 / scale
        if refine_c:
            q_fit_max = float(np.clip(1.5 * np.pi / (np.sqrt(5 / 3) * rg0), 0.06, 0.12))
            ref = refine_concentration(qv, Md2, E, c0, q_max=q_fit_max, q_min=0.018)
            c_ref = ref.pop("c")
            refine_info = ref
        C2 = np.array([c_ref, c_ref ** 2])
        P2 = Md2 @ np.linalg.pinv(C2)
        Pe2 = compute_propagated_error(Md2, P2[:, :1], E)
        rg = RgEstimator(np.array([qv, P2[:, 0], Pe2[:, 0]]).T).Rg
        if rg is None or not np.isfinite(rg) or rg <= 0:
            rg = rg0
        e = envelope_prior_lrf(qv, Mk, Md2, E, c_ref, float(rg), L=L, k_window=k_window, k_rule=k_rule)
        A = e["A"] / scale
        P_out[:, k] = A
        P_out[:, b_col] = e["r_post"] * A / scale             # M ~ A_ref c_ref + r A_ref c_ref^2 with c_ref = c0/scale: A = A_ref/scale, B = r A_ref/scale^2 = r A/scale
        b1 = np.pi / (np.sqrt(5 / 3) * rg)
        above = (qv >= b1) & (qv < BAND_FACTOR * b1) & np.isfinite(e["r_hat"])      # the band only: above it the ratio of two small numbers is not reliable
        with np.errstate(invalid="ignore"):
            viol = float(np.mean((np.abs(e["r_hat"][above]) - 2 * e["s_r"][above]) > 2 * e["tau"][above])) if above.any() else 0.0
        mid = (qv >= 1.5 / rg) & (qv < 3.5 / rg)
        w = e["tau"] ** 2 / (e["tau"] ** 2 + e["s_r"] ** 2)
        info[k] = EnvelopePriorInfo(
            K=e["K"], sigma=e["sigma"], L=float(L), rg_seed=float(rg), cutoff_q=float(b1),
            r_hat=e["r_hat"], s_r=e["s_r"], tau=e["tau"], r_post=e["r_post"],
            weight_mid=float(np.mean(w[mid])) if mid.any() else float("nan"), violation_fraction=viol,
            c_refined=c_ref if refine_c else None, c_scale=scale, refine=refine_info, q_min_used=float(np.min(qv)))
        reasons = info[k].warnings_list()
        if reasons and warn:
            warnings.warn(f"Envelope-prior LRF, component {k}: " + "; ".join(reasons) + " (see decomposition.envelope_prior_info)", UserWarning, stacklevel=2)
    return P_out[:, :num_components], info
