"""
    LowRank.ErrorScale.py

    Is the stated error column on the right scale, and do the component curves describe the data? (molass-library#416;
    molass-researcher experiment 65k, notebooks 65k_error_scale_explained and 65l_dof_explained.)

    Two different questions that a single reduced chi-square cannot separate:

    * **Noise scale** (:func:`compute_error_scale`): the true scatter of the data in units of the stated error, ``s_noise``,
      estimated *without any model* from a difference of order 4 over neighbouring frames (the 2nd difference
      ``M[:, j-1] - 2 M[:, j] + M[:, j+1]`` is the same idea with order 2). A smooth signal cancels (a polynomial of degree < order
      exactly; the fourth difference is used because a high signal-to-noise peak leaks its curvature into the second), independent
      noise of standard deviation sigma gives ``var(d) = C(2 order, order) sigma^2`` (6 or 70), so ``s_noise = sqrt(mean((d/E)^2) / 70)``. It recovers a known
      noise factor within a few percent (1.0 -> 1.00-1.02, 2.5 -> 2.46-2.52 on simulated frames). Needs a signal that is smooth
      over the frames and noise that is independent between frames.
    * **Lack of fit of the component curves** (:func:`compute_curve_fit_report`): ``s_curves = sqrt(chi2/dof)`` of a per-q-row
      weighted least-squares fit of the measured matrix with the component curves of a decomposition, compared with
      ``s_free`` of a free SVD fit of the same rank (rows whitened by their error). If ``s_free`` is about 1 and ``s_curves`` is
      well above it, the stated error is right and the *curves* do not describe the data.

    Both are reported per q region (the scale is not the same at every q). On the real SAMPLE3: ``s_noise`` is 0.94-1.0 for
    q >= 0.02 (the stated errors are right; 0.5-0.9 below, pessimistic), while the fit with the library's EGH component curve
    has ``s_curves`` up to about 5.6 near q = 0.035 (the reduced chi-square of 6 that looked like "errors 2.5x too small");
    a free rank-1 SVD fit is at 1.0-1.1 there.

    Degrees of freedom: a per-row fit with ``k`` curves has ``N - k`` (N frames); the free SVD fit uses ``N - k`` per row as well,
    the large-``n_q`` form of ``(n_q - k)(N - k)``.
"""
from dataclasses import dataclass
from math import comb
import warnings
import numpy as np

DEFAULT_REGIONS = (0.0, 0.02, 0.04, 0.1, 0.2, np.inf)     # q region edges in 1/Angstrom
LOW, HIGH = 1 / 1.5, 1.5                                    # s outside this interval triggers the warning
MIN_ROWS = 5                                                # regions with fewer q rows are not reported


def _frame_index(M, frames, min_fraction=0.05):
    if frames is None:
        total = M.sum(axis=0)
        return np.flatnonzero(total > min_fraction * total.max())
    if isinstance(frames, str):
        if frames == "all":
            return np.arange(M.shape[1])
        raise ValueError("frames must be None, 'all' or an index array")
    return np.asarray(frames)


def region_labels(edges):
    return [f"{a:g}-{b:g}" if np.isfinite(b) else f">={a:g}" for a, b in zip(edges[:-1], edges[1:])]


def _pooled(q, num, cnt, edges):
    """Pooled sqrt(sum num / sum cnt) per region from per-row sums; NaN where fewer than MIN_ROWS rows."""
    out = np.full(len(edges) - 1, np.nan)
    for r, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        m = (q >= a) & (q < b) & (cnt > 0)
        if m.sum() >= MIN_ROWS:
            out[r] = np.sqrt(np.sum(num[m]) / np.sum(cnt[m]))
    return out


@dataclass
class ErrorScaleReport:
    """Model-free noise scale of the stated error column, per q region.

    Attributes
    ----------
    regions : list of str
        Region labels (q edges in 1/Angstrom).
    edges : numpy.ndarray
    s_noise : numpy.ndarray
        True scatter / stated error per region (1: the stated error is right, 2.5: it is 2.5 times too small, 0.5: 2 times too large);
        NaN for regions with fewer than ``MIN_ROWS`` q points.
    s_noise_q : numpy.ndarray
        The same per q row (noisy: about 10 % scatter with 100 frames).
    num_frames : int
        Frames used.
    """
    regions: list
    edges: np.ndarray
    s_noise: np.ndarray
    s_noise_q: np.ndarray
    qv: np.ndarray
    num_frames: int

    def outside(self, low=LOW, high=HIGH):
        """Labels and values of the regions whose noise scale is outside ``[low, high]``."""
        return [(lab, float(s)) for lab, s in zip(self.regions, self.s_noise) if np.isfinite(s) and (s < low or s > high)]

    def __repr__(self):
        body = ", ".join(f"{lab}: {s:.2f}" for lab, s in zip(self.regions, self.s_noise) if np.isfinite(s))
        return f"ErrorScaleReport(true scatter / stated error by q region (1/A): {body}; frames={self.num_frames})"


def compute_error_scale(xr, frames=None, regions=None, warn=True, min_fraction=0.05, order=4):
    """See :meth:`molass.DataObjects.XrData.XrData.error_scale`."""
    if xr.E is None:
        raise ValueError("the XR data have no stated error (E is None)")
    M = np.asarray(xr.M, dtype=float)
    E = np.asarray(xr.E, dtype=float)
    q = np.asarray(xr.qv, dtype=float)
    if order < 2 or order % 2:
        raise ValueError("order must be an even integer >= 2")
    sel = np.zeros(M.shape[1], dtype=bool)
    sel[_frame_index(M, frames, min_fraction)] = True
    h = order // 2
    D = np.diff(M, n=order, axis=1)                         # D[:, i] is centred on frame i + h
    center = np.arange(D.shape[1]) + h
    keep = sel[center]
    if keep.sum() < 5:
        raise ValueError("fewer than 5 usable frames to estimate the scatter between neighbouring frames")
    Ec = E[:, center[keep]]
    z2 = (D[:, keep] / Ec) ** 2
    ok = np.isfinite(z2) & (Ec > 0)
    num = np.where(ok, z2, 0.0).sum(axis=1) / comb(2 * order, order)   # var(order-th difference) = C(2 order, order) sigma^2 (6 for order 2, 70 for order 4)
    cnt = ok.sum(axis=1).astype(float)
    edges = np.asarray(DEFAULT_REGIONS if regions is None else regions, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        s_q = np.sqrt(num / np.where(cnt > 0, cnt, np.nan))
    report = ErrorScaleReport(regions=region_labels(edges), edges=edges, s_noise=_pooled(q, num, cnt, edges),
                              s_noise_q=s_q, qv=q, num_frames=int(keep.sum()))
    if warn:
        bad = report.outside()
        if bad:
            txt = ", ".join(f"q {lab}: {s:.2f}" for lab, s in bad)
            warnings.warn(f"the stated error looks off in some q regions (true scatter / stated error: {txt}; 1 is right, "
                          f"above 1 the stated error is too small); see XrData.error_scale()", UserWarning, stacklevel=3)
    return report


def _fit_curves(M, E, C):
    """Per q row weighted least squares of M on the rows of C (k, n_frames); returns the residual sum of squares / E^2 per row."""
    W = 1.0 / E ** 2
    G = np.einsum("qf,kf,lf->qkl", W, C, C)
    b = np.einsum("qf,kf,qf->qk", W, C, M)
    sol = np.einsum("qkl,ql->qk", np.linalg.pinv(G), b)
    R = (M - sol @ C) / E
    return np.sum(R ** 2, axis=1)


def _fit_free_svd(M, E, rank):
    """Rank-``rank`` SVD fit of M (rows whitened by their median error); residual sum of squares / E^2 per row."""
    e = np.median(E, axis=1)
    U, S, Vt = np.linalg.svd(M / e[:, None], full_matrices=False)
    Mk = ((U[:, :rank] * S[:rank]) @ Vt[:rank]) * e[:, None]
    return np.sum(((M - Mk) / E) ** 2, axis=1)


@dataclass
class CurveFitReport:
    """Do the component curves describe the measured data? Per q region, ``s = sqrt(chi2 / dof)`` in units of the stated error.

    Attributes
    ----------
    regions : list of str
    s_curves : numpy.ndarray
        Per-q-row fit with the component curves of the decomposition (scales fitted per row).
    s_free : numpy.ndarray
        A free SVD fit of the same rank. About the noise scale where the data are rank-k.
    ratio : numpy.ndarray
        ``s_curves / s_free``; well above 1.5 means the curves, not the stated error or the rank, are what is wrong.
    s_curves_q, s_free_q : numpy.ndarray
        The same per q row.
    num_components, num_frames : int
    """
    regions: list
    edges: np.ndarray
    s_curves: np.ndarray
    s_free: np.ndarray
    ratio: np.ndarray
    s_curves_q: np.ndarray
    s_free_q: np.ndarray
    qv: np.ndarray
    num_components: int
    num_frames: int

    def misfit_regions(self, ratio=1.5):
        """Labels, ``s_curves`` and ``s_free`` of the regions where the curves fit the data ``ratio`` times worse than a free fit."""
        return [(lab, float(a), float(b)) for lab, a, b, r in zip(self.regions, self.s_curves, self.s_free, self.ratio)
                if np.isfinite(r) and r > ratio]

    def __repr__(self):
        rows = "; ".join(f"{lab}: curves {a:.2f} / free {b:.2f}" for lab, a, b in zip(self.regions, self.s_curves, self.s_free) if np.isfinite(a))
        return f"CurveFitReport(k={self.num_components}, s by q region (1/A): {rows}; frames={self.num_frames})"


def compute_curve_fit_report(decomposition, min_fraction=0.05, regions=None):
    """See :meth:`molass.LowRank.Decomposition.Decomposition.get_curve_fit_report`."""
    xr = decomposition.xr
    if xr.E is None:
        raise ValueError("the XR data have no stated error (E is None)")
    M = np.asarray(xr.M, dtype=float)
    E = np.asarray(xr.E, dtype=float)
    q = np.asarray(xr.qv, dtype=float)
    cols = _frame_index(M, None, min_fraction)
    C = np.array([np.asarray(c.get_xy()[1], dtype=float) for c in decomposition.xr_ccurves])[:, cols]
    k = C.shape[0]
    Mc, Ec = M[:, cols], E[:, cols]
    n = len(cols)
    if n <= k + 1:
        raise ValueError("too few frames for the number of components")
    dof = n - k
    chi_c = _fit_curves(Mc, Ec, C)
    chi_f = _fit_free_svd(Mc, Ec, k)
    edges = np.asarray(DEFAULT_REGIONS if regions is None else regions, dtype=float)
    cnt = np.full(len(q), float(dof))
    s_c, s_f = _pooled(q, chi_c, cnt, edges), _pooled(q, chi_f, cnt, edges)
    return CurveFitReport(regions=region_labels(edges), edges=edges, s_curves=s_c, s_free=s_f, ratio=s_c / s_f,
                          s_curves_q=np.sqrt(chi_c / dof), s_free_q=np.sqrt(chi_f / dof), qv=q, num_components=k, num_frames=int(n))
