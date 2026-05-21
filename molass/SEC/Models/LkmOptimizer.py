"""
SEC.Models.LkmOptimizer.py

Build LKM component curves from the output of LkmEstimator.

The optimizer uses the (Pe, t0, R_i, k_MT_i) returned by
``estimate_lkm_init_params`` and adjusts the per-component scale factors
with a simple non-negative least-squares fit against the integrated XR curve.

Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np


def optimize_lkm_xr_decomposition(decomposition, lkm_init_params, **kwargs):
    """
    Build ``LkmComponentCurve`` objects from LKM initial parameters.

    Parameters
    ----------
    decomposition : Decomposition
        EGH decomposition to upgrade.  Rg values are taken from
        ``decomposition.get_rgs()``.
    lkm_init_params : tuple
        ``(Pe, t0, k_MT_list, R_list, scale_list)`` as returned by
        :func:`~molass.SEC.Models.LkmEstimator.estimate_lkm_init_params`.

    Returns
    -------
    new_xr_ccurves : list of LkmComponentCurve
    """
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.LkmComponentCurve
        reload(molass.SEC.Models.LkmComponentCurve)
    from molass.SEC.Models.LkmComponentCurve import LkmComponentCurve

    Pe, t0, k_MT_list, R_list, scale_list = lkm_init_params

    xr_icurve = decomposition.xr_icurve
    x, y_obs = xr_icurve.get_xy()
    rgv = decomposition.get_rgs()

    num_components = decomposition.num_components

    # ── Refine per-component scales with NNLS ─────────────────────────────────
    # Build a basis matrix B where each column is lkm_pdf for one component.
    from molass.SEC.Models.LkmLinear import lkm_pdf
    B = np.column_stack([
        lkm_pdf(x, Pe, t0, k_MT_list[i], R_list[i])
        for i in range(num_components)
    ])
    # Non-negative least squares to find optimal scales
    from scipy.optimize import nnls
    scales_nnls, _ = nnls(B, np.maximum(y_obs, 0))

    # Fall back to estimator scales if NNLS gives zero for any component
    for i in range(num_components):
        if scales_nnls[i] < 1e-10:
            scales_nnls[i] = scale_list[i]

    if debug:
        print(f"LKM optimizer: Pe={Pe:.1f}  t0={t0:.2f}")
        for i in range(num_components):
            print(f"  comp {i}: R={R_list[i]:.3f}  k_MT={k_MT_list[i]:.4f}  "
                  f"scale_est={scale_list[i]:.4f}  scale_nnls={scales_nnls[i]:.4f}")

    new_xr_ccurves = []
    for i in range(num_components):
        rg_i = rgv[i] if rgv is not None else float('nan')
        ccurve = LkmComponentCurve(
            x, Pe, t0,
            k_MT  = k_MT_list[i],
            R     = R_list[i],
            scale = scales_nnls[i],
            rg    = rg_i,
        )
        new_xr_ccurves.append(ccurve)

    return new_xr_ccurves
