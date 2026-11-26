"""
    LowRank.ConcentrationRefine.py

    Refinement of the concentration curve inside the rank-2 (interparticle) fit (decision D1 of molass-researcher experiment 65).

    With an interparticle effect the apparent XR elution curve is distorted by the c^2 term (it flattens the top of the peak), so
    the fitted component curve is a poor ``c(t)`` for the rows ``[c; c^2]``: in simulations the low-q error of the c^2 correction was
    0.2-0.3 with the library's XR curve against 0.006 with the true curve, and a 10 % width error of c multiplied it by 6.

    The refinement fits ``c(t)`` together with the interaction to the matrix itself, over ``q_min <= q < q_max``:

        M(q, t) ~ A(q) [ c(t) - K Phi(2 q R_eff) c(t)^2 ]

    with A(q) profiled out per q (weights 1/E^2). Two steps: (1) a parametric change of the start curve (width scale ``w`` about the peak,
    offset ``o``, shift ``s`` in frames) together with K and R_eff; (2) a free ``c(t)`` (one value per frame, Whittaker-smoothed), alternating
    with the K, R_eff fit until the largest change of c is below ``tol``. No UV curve is needed (a UV-derived curve carries the risk of a
    wrong UV->XR mapping). The hard-sphere form of the interaction is used here only to *identify* c; the correction itself is done by the
    envelope-prior LRF (:mod:`molass.LowRank.EnvelopePrior`), which assumes no shape of B(q).

    Caveat: the refined c is not independent of the assumed interaction shape. In simulations with other interactions (experiment 66) the
    result was still much better than the unrefined curve, but the refined curve is an *effective* curve for the c^2 model.
"""
import numpy as np
from scipy.optimize import minimize
from molass.SAXS.Theory.SolidSphere import phi

BOUNDS = dict(K=(0.0, 3.0), logR=(np.log(10.0), np.log(400.0)), w=(0.8, 1.25), o=(-0.05, 0.05), s=(-4.0, 4.0))


def transform_curve(c0n, w, o, s):
    """``c0n`` (peak 1) stretched by ``w`` about its peak, shifted by ``s`` frames, minus ``o``."""
    j = np.arange(len(c0n), dtype=float)
    pk = float(np.argmax(c0n))
    return np.interp(pk + (j - pk - s) / w, j, c0n) - o


def fit_parametric(q, M, E, c0, q_max=0.12, q_min=0.0, free_c=True):
    """Step 1 (and the (K, R_eff) step of step 2 with ``free_c=False``). Returns dict(K, Re, w, o, s, c (peak 1), at_bound, chi2)."""
    c0n = np.asarray(c0, float) / np.max(c0)
    mask = (q >= q_min) & (q < q_max)
    qm, Mm, W = q[mask], M[mask], 1.0 / E[mask] ** 2
    base = np.sum(W * Mm ** 2)

    def chi(p):
        K, lR, w, o, s = p
        c = transform_curve(c0n, w, o, s) if free_c else c0n
        g = c[None, :] - K * phi(qm, 2 * np.exp(lR))[:, None] * (c ** 2)[None, :]
        num = np.sum(W * Mm * g, axis=1)
        den = np.sum(W * g * g, axis=1)
        return float(base - np.sum(num ** 2 / np.maximum(den, 1e-300)))

    bnds = [BOUNDS["K"], BOUNDS["logR"], BOUNDS["w"] if free_c else (1.0, 1.0), BOUNDS["o"] if free_c else (0.0, 0.0), BOUNDS["s"] if free_c else (0.0, 0.0)]
    best = None
    for R0 in (20.0, 45.0, 90.0, 180.0):
        r = minimize(chi, (0.3, np.log(R0), 1.0, 0.0, 0.0), method="L-BFGS-B", bounds=bnds)
        if best is None or r.fun < best.fun:
            best = r
    K, lR, w, o, s = best.x
    at_bound = bool(np.exp(lR) < 10.5 or np.exp(lR) > 380 or K > 2.95 or (free_c and (w < 0.805 or w > 1.245 or abs(o) > 0.0495 or abs(s) > 3.95)))
    c = transform_curve(c0n, w, o, s) if free_c else c0n
    return dict(K=float(K), Re=float(np.exp(lR)), w=float(w), o=float(o), s=float(s), c=c, at_bound=at_bound, chi2=float(best.fun))


def fit_free_curve(q, M, E, c_start, K0, R0, q_max=0.12, q_min=0.0, n_outer=40, smooth=2.0, n_newton=4, tol=2e-4):
    """Step 2: a free ``c(t)``. Alternates the per-q profile of A, a Gauss-Newton step of c per frame and the (K, R_eff) fit, with a Whittaker
    smoothing (``smooth`` x second differences) after every c-step, until the largest change of c is below ``tol`` (the alternation converges slowly:
    8 iterations were not enough in the experiments). c is kept at peak 1 (K absorbs the scale). Returns the dict of :func:`fit_parametric`
    plus ``converged`` and ``n_iter`` (w, o, s are NaN)."""
    from scipy.sparse import diags, identity
    from scipy.sparse.linalg import splu
    mask = (q >= q_min) & (q < q_max)
    qm, Mm, W = q[mask], M[mask], 1.0 / E[mask] ** 2
    nf = M.shape[1]
    D = diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(nf - 2, nf))
    S = splu((identity(nf) + smooth * (D.T @ D)).tocsc())
    c = np.asarray(c_start, float) / np.max(c_start)
    K, R = K0, R0
    fit, converged, it = None, False, 0
    for it in range(1, n_outer + 1):
        c_prev = c
        ph = phi(qm, 2 * R)
        g = c[None, :] - K * ph[:, None] * (c ** 2)[None, :]
        A = np.sum(W * Mm * g, axis=1) / np.maximum(np.sum(W * g * g, axis=1), 1e-300)
        a, b = A, K * ph * A
        for _ in range(n_newton):
            r = Mm - a[:, None] * c[None, :] + b[:, None] * (c ** 2)[None, :]
            J = -a[:, None] + 2 * b[:, None] * c[None, :]
            c = c - np.sum(W * r * J, axis=0) / np.maximum(np.sum(W * J * J, axis=0), 1e-300)
        c = S.solve(c)
        lam = np.max(c)
        c = c / lam
        K = K * lam
        fit = fit_parametric(q, M, E, c, q_max=q_max, q_min=q_min, free_c=False)
        K, R = fit["K"], fit["Re"]
        if it >= 4 and float(np.max(np.abs(c - c_prev))) < tol:
            converged = True
            break
    fit.update(w=float("nan"), o=float("nan"), s=float("nan"), c=c, converged=converged, n_iter=it)
    return fit


def refine_concentration(qv, M, E, c, q_max=0.12, q_min=0.018, free=True):
    """Refine the concentration curve ``c`` (one value per frame, any scale) against the matrix ``M`` (n_q, n_frames) with the stated error ``E``.

    Parameters
    ----------
    qv : array, shape (n_q,)
    M, E : array, shape (n_q, n_frames)
        The matrix of the component (other components removed) and its stated error. A whitened rank-2 denoised matrix is the better input
        (:func:`molass.LowRank.LowRankInfo.get_weighted_denoised_data`).
    c : array, shape (n_frames,)
        The start curve (the library's fitted component curve).
    q_max, q_min : float
        The q range of the fit (1/Angstrom). ``q_max`` of about ``1.5 pi / R`` capped to 0.06-0.12 (the experiments: K and R_eff do not depend on it between 0.06 and 0.20).
    free : bool
        ``False`` stops after the parametric step (width, offset, shift).

    Returns
    -------
    dict
        ``c`` (the refined curve at peak 1), ``K``, ``Re`` (the fitted interaction strength and hard-sphere radius, only auxiliary),
        ``at_bound`` (a parameter ended at its bound: the fit did not find a hard-sphere-like effect, do not trust K and Re),
        ``w``, ``o``, ``s`` (the parametric step), ``converged`` and ``n_iter`` of the free step.
    """
    qv = np.asarray(qv, float)
    M = np.asarray(M, float)
    E = np.asarray(E, float)
    par = fit_parametric(qv, M, E, c, q_max=q_max, q_min=q_min)
    if not free:
        par.update(converged=True, n_iter=0)
        return par
    fr = fit_free_curve(qv, M, E, par["c"], par["K"], par["Re"], q_max=q_max, q_min=q_min)
    out = fit_parametric(qv, M, E, fr["c"], q_max=q_max, q_min=q_min, free_c=False)     # K, R_eff on the final curve
    out.update(w=par["w"], o=par["o"], s=par["s"], c=fr["c"], converged=fr["converged"], n_iter=fr["n_iter"], at_bound=bool(out["at_bound"] or par["at_bound"]))
    return out
