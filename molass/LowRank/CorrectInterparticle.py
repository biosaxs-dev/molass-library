"""
    LowRank.CorrectInterparticle.py

    ``correct_interparticle(M, c, qv, ...)`` (molass-library#414): the interparticle correction of one component on arrays, with a selectable method, without
    a ``Decomposition``: for comparisons, tutorials, stress tests (an Rg error) and papers. ``Decomposition.get_xr_matrices()`` keeps its own path; for one
    component with the library's curve and the stated error the two give the same A(q).
"""
from dataclasses import dataclass, field
from types import SimpleNamespace

import numpy as np

METHODS = ('soft_bounded', 'bounded', 'simple', 'rank1')


@dataclass
class InterparticleResult:
    """Result of :func:`correct_interparticle`.

    Attributes
    ----------
    A, B : ndarray, shape (n_q,)
        ``M ~ A c + B c^2`` with ``c`` the curve of ``c_used`` (so ``A c_peak`` is the profile at the peak). ``B`` is zeros for ``'rank1'``.
    method : str
    qv : ndarray
    c_used : ndarray
        The concentration curve the result refers to: the given ``c``, or the refined curve in the units of ``c`` for the soft-bounded LRF (``refine_c=True``).
    rg : float or None
        The Guinier Rg the bound followed (``sigma = 2 sqrt(5/3) Rg`` for the soft-bounded LRF, ``R = sqrt(5/3) Rg`` for the Bounded LRF); ``rg_given`` says whether
        it was the ``rg`` argument. ``None`` for ``'simple'`` and ``'rank1'``.
    info : SoftBoundedInfo, BoundedLrfInfo or None
        The diagnostics of the method (``warnings_list()``).
    warnings : list of str
        ``info.warnings_list()``.
    """
    A: np.ndarray
    B: np.ndarray
    method: str
    qv: np.ndarray
    c_used: np.ndarray
    rg: float = None
    rg_given: bool = False
    info: object = None
    warnings: list = field(default_factory=list)

    def __repr__(self):
        parts = [f"method={self.method!r}", f"n_q={len(self.qv)}"]
        if self.rg is not None:
            parts.append(f"rg={self.rg:.2f}{' (given)' if self.rg_given else ''}")
        if self.info is not None and 'K' in self.info:
            parts.append(f"K={self.info['K']:.3g}")
        parts.append(f"warnings={len(self.warnings)}")
        return f"InterparticleResult({', '.join(parts)})"


def _denoise(M, E, rank):
    from molass.LowRank.LowRankInfo import get_denoised_data, get_weighted_denoised_data
    return get_weighted_denoised_data(M, E, rank) if E is not None else get_denoised_data(M, rank)


def correct_interparticle(M, c, qv, *, error=None, method='soft_bounded', rg=None, denoise=True, warn=True, **options):
    """
    The interparticle correction of one component on arrays: ``M ~ A c + B c^2``.

    Parameters
    ----------
    M : ndarray, shape (n_q, n_frames)
        The data matrix of the component (e.g. ``ssd.xr.M`` for one species; frames on the same grid as ``c``).
    c : ndarray, shape (n_frames,)
        The concentration curve, **required**: the accuracy of every c^2 correction is limited by it more than by the method (molass-researcher experiments
        65-66). Ideally derived from the UV signal on the frame grid of ``M``; the units are free (the result is per unit of ``c``).
    qv : ndarray, shape (n_q,)
    error : ndarray, shape (n_q, n_frames) or None
        The stated error (``ssd.xr.E``). Needed by ``'soft_bounded'``; when given, the SVD denoising is whitened per q row (molass-library#418).
    method : {'soft_bounded', 'bounded', 'simple', 'rank1'}
        ``'soft_bounded'`` (default, as for rank-2 components of a ``Decomposition``): :mod:`molass.LowRank.SoftBoundedLrf`; ``'bounded'``: the hard-clip
        :mod:`molass.LowRank.BoundedLrf` (assumes hard spheres, ``R = sqrt(5/3) Rg``); ``'simple'``: the plain c^2 fit ``M_ pinv([c; c^2])`` with no guard
        (noisy at high q); ``'rank1'``: no correction ``M_ pinv(c)`` (``B`` is zeros). The Synthesized splice of the legacy code is not offered.
    rg : float or None
        ``None``: the Guinier Rg of the A(q) of the plain c^2 fit, as the pipeline does. A number overrides it, e.g. for a stress test of an Rg error: the
        Bounded LRF uses it for ``R`` and the soft-bounded LRF for ``sigma`` and the cut-off.
    denoise : bool
        Denoise ``M`` by the rank-1 (``'rank1'``) or rank-2 (the others) SVD first, as the pipeline does (default). ``False`` uses ``M`` as it is.
    warn : bool
        Emit the ``UserWarning`` of the method when its diagnostics deserve a second look (the texts are in ``result.warnings`` in any case).
    **options
        For ``'soft_bounded'``: ``refine_c`` (default ``True``), ``L``, ``k_window``, ``k_rule`` (see ``Decomposition.set_rank2_method``).

    Returns
    -------
    InterparticleResult

    Example
    -------
    ::

        res = correct_interparticle(M, c, qv, error=E)                      # soft-bounded LRF
        bad = correct_interparticle(M, c, qv, error=E, method='bounded', rg=1.2 * rg_true)   # an Rg error
        res.A, res.B, res.rg, res.warnings
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; use one of {METHODS}")
    if options and method != 'soft_bounded':
        raise ValueError(f"the options {sorted(options)} are for method='soft_bounded' only")
    qv = np.asarray(qv, dtype=float)
    M = np.asarray(M, dtype=float)
    c = np.asarray(c, dtype=float)
    E = None if error is None else np.asarray(error, dtype=float)
    if M.ndim != 2 or M.shape[0] != len(qv) or M.shape[1] != len(c):
        raise ValueError(f"M must have shape (len(qv), len(c)) = ({len(qv)}, {len(c)}), not {M.shape}")
    if E is not None and E.shape != M.shape:
        raise ValueError(f"error must have the shape of M {M.shape}, not {E.shape}")
    if method == 'soft_bounded' and E is None:
        raise ValueError("the soft-bounded LRF needs the stated error: pass error=..., or use method='bounded', 'simple' or 'rank1'")

    if method == 'rank1':
        M_ = _denoise(M, E, 1) if denoise else M
        A = (M_ @ np.linalg.pinv(c.reshape(1, -1)))[:, 0]
        return InterparticleResult(A=A, B=np.zeros_like(A), method=method, qv=qv, c_used=c)

    M_ = _denoise(M, E, 2) if denoise else M
    C_full = np.array([c, c ** 2])
    P_full = M_ @ np.linalg.pinv(C_full)
    if method == 'simple':
        return InterparticleResult(A=P_full[:, 0], B=P_full[:, 1], method=method, qv=qv, c_used=c)

    # the Rg that seeds the bound: the Guinier Rg of A(q) of the plain c^2 fit (as Decomposition.get_xr_matrices), unless given
    if rg is None:
        from molass.Guinier.RgEstimator import RgEstimator
        from molass.LowRank.ErrorPropagate import compute_propagated_error
        Pe = np.ones((len(qv), 1)) if E is None else compute_propagated_error(M_, P_full[:, :1], E)
        seed = RgEstimator(np.array([qv, P_full[:, 0], Pe[:, 0]]).T)
    else:
        seed = SimpleNamespace(Rg=float(rg))
    if seed.Rg is None or not np.isfinite(seed.Rg) or seed.Rg <= 0:
        raise ValueError("no valid Guinier Rg for the bound (the plain-fit profile has no Guinier region): pass rg=...")

    if method == 'bounded':
        from molass.LowRank.BoundedLrf import apply_bounded_lrf
        A_out, infos = apply_bounded_lrf(qv, P_full, C_full, [2], [seed], warn=warn)
        info = infos[0]
        return InterparticleResult(A=A_out[:, 0], B=np.asarray(info['bq_coerced']), method=method, qv=qv, c_used=c, rg=float(info['Rg']),
                                   rg_given=rg is not None, info=info, warnings=info.warnings_list())

    from molass.LowRank.SoftBoundedLrf import apply_soft_bounded_lrf
    A_out, infos = apply_soft_bounded_lrf(qv, M, E, C_full, P_full, [2], [seed], warn=warn, rg_fixed=None if rg is None else float(rg), **options)
    info = infos[0]
    A = A_out[:, 0]
    scale = info['c_scale']
    c_used = c if info['c_refined'] is None else info['c_refined'] * scale
    B = info['r_post'] * A / scale                                          # M ~ A c_used + B c_used^2 (A is per unit of c at its peak)
    return InterparticleResult(A=A, B=B, method=method, qv=qv, c_used=c_used, rg=float(info['rg_seed']), rg_given=rg is not None,
                               info=info, warnings=info.warnings_list())
