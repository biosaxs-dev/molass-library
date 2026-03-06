"""
LowRank.AlignDecompositions.py

Utility for aligning scattering profiles from two decompositions onto a
common q-grid. Exported at the top-level as ``molass.align_decompositions``.
"""
import numpy as np


def get_P_at(decomp, q_target, normalize=False):
    """
    Return the XR scattering matrix P interpolated onto *q_target*.

    Parameters
    ----------
    decomp : Decomposition
        A decomposition object returned by ``quick_decomposition()``.
    q_target : array-like, shape (m,)
        Target q-values in Å⁻¹.  Must lie within the q-range of *decomp*.
    normalize : bool, optional
        If ``True``, each component column is divided by its maximum value
        so that all columns peak at 1.  Default ``False``.

    Returns
    -------
    P_interp : np.ndarray, shape (m, n_components)
        Scattering matrix P evaluated at *q_target*.
    """
    _, _, P, _ = decomp.get_xr_matrices()
    qv = decomp.xr.qv
    q_target = np.asarray(q_target)
    P_interp = np.column_stack([
        np.interp(q_target, qv, P[:, i]) for i in range(P.shape[1])
    ])
    if normalize:
        col_max = P_interp.max(axis=0)
        col_max[col_max == 0] = 1.0          # avoid division by zero
        P_interp = P_interp / col_max
    return P_interp


def align_decompositions(decomp_a, decomp_b, n=500, normalize=False):
    """
    Interpolate two decompositions' XR scattering matrices onto a shared q-grid.

    The shared grid spans the intersection of the two q-ranges and contains
    *n* evenly-spaced points.

    Parameters
    ----------
    decomp_a, decomp_b : Decomposition
        Two decomposition objects to align.
    n : int, optional
        Number of q-points in the common grid.  Default 500.
    normalize : bool, optional
        If ``True``, each component column in both matrices is normalised to
        peak at 1.  Useful for shape comparison regardless of absolute scale.
        Default ``False``.

    Returns
    -------
    q_common : np.ndarray, shape (n,)
        The shared q-grid in Å⁻¹.
    P_a : np.ndarray, shape (n, n_components_a)
        Scattering matrix of *decomp_a* evaluated on *q_common*.
    P_b : np.ndarray, shape (n, n_components_b)
        Scattering matrix of *decomp_b* evaluated on *q_common*.

    Examples
    --------
    Compare the first scattering component of two decompositions::

        from scipy.stats import pearsonr
        import molass

        q, P_a, P_b = molass.align_decompositions(decomp_1, decomp_2, normalize=True)
        r, _ = pearsonr(P_a[:, 0], P_b[:, 0])
        print(f"Pearson r = {r:.5f}")
    """
    q_a = decomp_a.xr.qv
    q_b = decomp_b.xr.qv
    q_lo = max(q_a[0], q_b[0])
    q_hi = min(q_a[-1], q_b[-1])
    if q_lo >= q_hi:
        raise ValueError(
            f"q-ranges do not overlap: [{q_a[0]:.4f}, {q_a[-1]:.4f}] vs "
            f"[{q_b[0]:.4f}, {q_b[-1]:.4f}]"
        )
    q_common = np.linspace(q_lo, q_hi, n)
    P_a = get_P_at(decomp_a, q_common, normalize=normalize)
    P_b = get_P_at(decomp_b, q_common, normalize=normalize)
    return q_common, P_a, P_b
