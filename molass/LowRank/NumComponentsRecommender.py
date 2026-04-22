"""
LowRank.NumComponentsRecommender — recommend ``num_components`` for SDM-style
decompositions by detecting degeneracy when an extra component is added.

Background
----------
Setting ``num_components`` one too high for the data is a common failure mode
of SDM (and SDM-rigorous) optimization: the extra component's elution profile
collapses onto an existing one, ``cond(C)`` blows up, and ``optimize_rigorously``
later stalls at SV ≈ 51 ("Poor"). The diagnostic implemented here was
verified across 7 datasets (SAMPLE1-4 + Apo + ATP + MY) in
``molass-researcher/experiments/13_rigorous_optimization/13aa_num_components_diagnostic.ipynb``
(see issue #116 for the full table).
"""
from collections import namedtuple
import contextlib
import io
import warnings

import numpy as np
import pandas as pd


Recommendation = namedtuple(
    "Recommendation",
    ["recommended_k", "reason", "metrics"],
)
"""Result of :meth:`Decomposition.recommend_num_components`.

Attributes
----------
recommended_k : int or None
    The recommended ``num_components``. ``None`` if no fit succeeded.
reason : str
    Human-readable justification for the choice.
metrics : pandas.DataFrame
    One row per ``k`` actually fitted, with columns
    ``['k', 'residual', 'cond_C', 'max_cos', 'amp_ratio', 'flag_count', 'status']``.
"""


# Default thresholds for the three degeneracy flags. Verified in 13aa across
# 7 datasets x k in {1,2,3}; no dataset trips a flag when k matches the true
# number of components.
DEFAULT_COND_THRESHOLD = 50.0
DEFAULT_COS_THRESHOLD = 0.99
DEFAULT_AMP_THRESHOLD = 0.20


def _diagnose(decomp):
    """Compute (residual, cond_C, max_cos, amp_ratio, n) for a Decomposition.

    P is solved as ``M @ pinv(C)``; residual is ``||M - PC||_F / ||M||_F``.
    """
    C = np.array([c.y for c in decomp.xr_ccurves])  # (k, frames)
    M = decomp.ssd.xr.M                              # (q, frames)
    P = M @ np.linalg.pinv(C)                        # (q, k)

    res = float(np.linalg.norm(M - P @ C) / np.linalg.norm(M))

    try:
        cond_C = float(np.linalg.cond(C))
    except Exception:
        cond_C = float("inf")

    n = C.shape[0]
    if n == 1:
        max_cos = float("nan")
    else:
        norms = np.linalg.norm(C, axis=1)
        gram = (C @ C.T) / np.outer(norms, norms)
        np.fill_diagonal(gram, 0.0)
        max_cos = float(np.max(np.abs(gram)))

    # numpy>=2 renamed trapz -> trapezoid
    _trapz = getattr(np, "trapezoid", getattr(np, "trapz"))
    areas = _trapz(np.maximum(C, 0), axis=1)
    if n == 1 or areas.max() == 0:
        amp_ratio = float("nan")
    else:
        amp_ratio = float(areas.min() / areas.max())

    return res, cond_C, max_cos, amp_ratio, n


def _count_flags(row, cond_thr, cos_thr, amp_thr):
    f = 0
    if row["cond_C"] > cond_thr:
        f += 1
    if row["max_cos"] > cos_thr:
        f += 1
    if row["amp_ratio"] < amp_thr:
        f += 1
    return f


def recommend_num_components(
    decomp,
    k_max=3,
    model="SDM",
    rgcurve=None,
    rt_dist="gamma",
    cond_threshold=DEFAULT_COND_THRESHOLD,
    cos_threshold=DEFAULT_COS_THRESHOLD,
    amp_threshold=DEFAULT_AMP_THRESHOLD,
    quiet=True,
    debug=False,
):
    """Recommend ``num_components`` by detecting degeneracy at ``k+1``.

    For each ``k in 1..k_max``, runs a fresh
    ``ssd.quick_decomposition(num_components=k).optimize_with_model(model, ...)``
    on ``decomp.ssd``, then computes four diagnostics:

    - ``residual = ||M - PC|| / ||M||``  (P solved as ``M @ pinv(C)``)
    - ``cond_C  = np.linalg.cond(C)``
    - ``max_cos = max_{i<j} |C[i] . C[j]| / (||C[i]|| ||C[j]||)``
    - ``amp_ratio = min_i area_i / max_i area_i``

    **Decision rule**: pick the smallest ``k`` such that ``k+1`` either
    (a) **increases** the residual or (b) trips ``>=2`` of
    ``{cond_C > cond_threshold, max_cos > cos_threshold, amp_ratio < amp_threshold}``.
    If neither happens up to ``k_max``, return ``k_max`` with reason
    ``"no degeneracy detected up to k_max"``.

    Parameters
    ----------
    decomp : Decomposition
        Used only for ``decomp.ssd``; the decomposition itself is not modified.
    k_max : int, optional
        Maximum ``num_components`` to try. Default 3.
    model : str, optional
        Model name passed to :meth:`Decomposition.optimize_with_model`.
        Default ``'SDM'``.
    rgcurve : Curve, optional
        Rg curve to pass to ``optimize_with_model``. If ``None``, computed
        once via ``decomp.ssd.xr.compute_rgcurve()``.
    rt_dist : str, optional
        SDM residence-time distribution (``'gamma'`` or ``'exponential'``).
        Forwarded as ``model_params={'rt_dist': rt_dist}``.
    cond_threshold, cos_threshold, amp_threshold : float, optional
        Degeneracy thresholds.
    quiet : bool, optional
        Suppress per-fit stdout/stderr from the fitting machinery. Default True.
    debug : bool, optional
        If True, do not suppress output and forward ``debug=True`` downstream.

    Returns
    -------
    Recommendation
        Named tuple ``(recommended_k, reason, metrics)``. ``metrics`` is a
        ``pandas.DataFrame`` indexed-free with one row per ``k`` actually
        attempted (including failed ones, marked in the ``status`` column).

    Notes
    -----
    Verified across 7 datasets (SAMPLE1-4 + Apo + ATP + MY) - see issue #116.
    The diagnostic uses ``optimize_with_model`` (cheap, ~seconds per fit), not
    rigorous optimization.
    """
    ssd = decomp.ssd
    if rgcurve is None:
        if quiet and not debug:
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()), \
                 warnings.catch_warnings():
                warnings.simplefilter("ignore")
                rgcurve = ssd.xr.compute_rgcurve()
        else:
            rgcurve = ssd.xr.compute_rgcurve()

    rows = []
    for k in range(1, int(k_max) + 1):
        try:
            if quiet and not debug:
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()), \
                     warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    d_k = ssd.quick_decomposition(num_components=k)
                    d_opt = d_k.optimize_with_model(
                        model, rgcurve=rgcurve,
                        model_params={"rt_dist": rt_dist},
                        debug=debug)
            else:
                d_k = ssd.quick_decomposition(num_components=k)
                d_opt = d_k.optimize_with_model(
                    model, rgcurve=rgcurve,
                    model_params={"rt_dist": rt_dist},
                    debug=debug)
            res, cond_C, mcos, amp, _n = _diagnose(d_opt)
            rows.append(dict(k=k, residual=res, cond_C=cond_C,
                             max_cos=mcos, amp_ratio=amp, status="ok"))
        except Exception as exc:
            rows.append(dict(k=k, residual=float("nan"), cond_C=float("nan"),
                             max_cos=float("nan"), amp_ratio=float("nan"),
                             status=f"err:{type(exc).__name__}"))

    df = pd.DataFrame(rows)
    df["flag_count"] = df.apply(
        lambda r: _count_flags(r, cond_threshold, cos_threshold, amp_threshold)
        if r["status"] == "ok" else 0,
        axis=1,
    )
    df = df[["k", "residual", "cond_C", "max_cos", "amp_ratio",
             "flag_count", "status"]]

    ok = df[df.status == "ok"].sort_values("k").reset_index(drop=True)
    if ok.empty:
        return Recommendation(None, "no successful fits", df)

    chosen = None
    reason = ""
    ks = ok.k.tolist()
    for i, k in enumerate(ks[:-1]):
        cur = ok.iloc[i]
        nxt = ok.iloc[i + 1]
        if nxt["residual"] > cur["residual"]:
            chosen = int(k)
            reason = (f"residual increases at k={int(nxt['k'])} "
                      f"({cur['residual']:.3f} -> {nxt['residual']:.3f})")
            break
        if nxt["flag_count"] >= 2:
            chosen = int(k)
            reason = (f"k={int(nxt['k'])} trips "
                      f"{int(nxt['flag_count'])} degeneracy flags")
            break
    if chosen is None:
        chosen = int(ks[-1])
        reason = "no degeneracy detected up to k_max"

    return Recommendation(chosen, reason, df)
