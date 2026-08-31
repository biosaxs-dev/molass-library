"""
SEC.Models.GrmOptimizer.py

Build GRM component curves from the output of GrmEstimator.

NNLS scale refinement identical to LkmOptimizer, replacing lkm_pdf with grm_pdf.

Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np


def optimize_grm_xr_decomposition(decomposition, grm_init_params, **kwargs):
    """
    Build ``GrmComponentCurve`` objects from GRM initial parameters.

    Parameters
    ----------
    decomposition : Decomposition
        EGH decomposition to upgrade.  Rg values are taken from
        ``decomposition.get_rgs()``.
    grm_init_params : tuple
        ``(Pe, t0, R_p, D_eff, a_star, F_ratio, k_ext_list, R_list, c_inj)``
        as returned by :func:`~molass.SEC.Models.GrmEstimator.estimate_grm_init_params`.

    Returns
    -------
    new_xr_ccurves : list of GrmComponentCurve
    """
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.GrmComponentCurve
        reload(molass.SEC.Models.GrmComponentCurve)
    from molass.SEC.Models.GrmComponentCurve import GrmComponentCurve

    Pe, t0, R_p, D_eff, a_star_list, F_ratio, k_ext_list, R_list, c_inj_est = grm_init_params

    xr_icurve = decomposition.xr_icurve
    x, y_obs = xr_icurve.get_xy()
    rgv = decomposition.get_rgs()

    num_components = decomposition.num_components

    # ── Refine per-component scales with NNLS ─────────────────────────────────
    # Build normalized basis (c_inj=1.0, t_inj=1.0)
    from molass.SEC.Models.GrmLinear import grm_pdf
    B = np.column_stack([
        grm_pdf(x, Pe, t0, k_ext_list[i], R_p, D_eff, a_star_list[i], F_ratio,
                c_inj=1.0, t_inj=1.0)
        for i in range(num_components)
    ])
    from scipy.optimize import nnls
    scales_nnls, _ = nnls(B, np.maximum(y_obs, 0))
    
    # Convert NNLS scales to c_inj values (these are the actual per-component c_inj)
    cinj_list = scales_nnls.copy()

    for i in range(num_components):
        if cinj_list[i] < 1e-10:
            cinj_list[i] = c_inj_est  # fallback to estimator value

    if debug:
        print(f"GRM optimizer: Pe={Pe:.1f}  t0={t0:.2f}")
        for i in range(num_components):
            print(f"  comp {i}: R={R_list[i]:.3f}  k_ext={k_ext_list[i]:.5f}  "
                  f"c_inj_est={c_inj_est:.4f}  c_inj_nnls={cinj_list[i]:.4f}")

    new_xr_ccurves = []
    for i in range(num_components):
        rg_i = rgv[i] if rgv is not None else float('nan')
        ccurve = GrmComponentCurve(
            x, Pe, t0, R_p, D_eff, a_star_list[i], F_ratio,
            k_ext = k_ext_list[i],
            R     = R_list[i],
            c_inj = cinj_list[i],
            rg    = rg_i,
            t_inj = 1.0,
        )
        new_xr_ccurves.append(ccurve)

    return new_xr_ccurves
