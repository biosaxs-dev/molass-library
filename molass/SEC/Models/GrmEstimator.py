"""
SEC.Models.GrmEstimator.py

Estimate GRM (General Rate Model) initial parameters from EGH component moments.

Strategy
--------
1. Run the LKM estimator to get (Pe, t0, k_MT_i, R_i, scale_i).
2. Apply the moment-matching relationship (Qamar 2014, App C) to convert k_MT_i
   into k_ext_i, keeping all other parameters identical:

   k_MT_eff = k_MT_LKM * (R-1)/R
   k_ext    = k_MT_eff * R_p * R / (3 * F)
            = k_MT_LKM * (R-1) * R_p / (3 * F)

3. Shared column params (R_p, D_eff, a_star, F_ratio) are derived from column
   settings or reasonable defaults:
   - R_p     : SerialSettings("particle_radius") or default 0.0035 cm
   - D_eff   : SerialSettings("D_eff") or default 1e3 cm²/min (film-only limit)
   - eps_p   : SerialSettings("particle_porosity") or default 0.0 (non-porous)
   - eps_col : SerialSettings("column_porosity") or default 0.4

Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np

# Default particle geometry when SerialSettings are not available
DEFAULT_R_P   = 0.0035   # cm (≈ 70 µm diameter — typical SEC bead)
DEFAULT_D_EFF = 1e3      # cm²/min (very large → film-only limit; GRM ≈ LKM in shape)
DEFAULT_EPS_P = 0.0      # non-porous particles
DEFAULT_EPS   = 0.4      # interstitial column porosity


def _get_grm_column_settings():
    """Retrieve particle geometry from SerialSettings, falling back to defaults."""
    try:
        from molass_legacy._MOLASS.SerialSettings import get_setting
        R_p   = get_setting("particle_radius") or DEFAULT_R_P
        D_eff = get_setting("D_eff")           or DEFAULT_D_EFF
        eps_p = get_setting("particle_porosity") if get_setting("particle_porosity") is not None else DEFAULT_EPS_P
        eps   = get_setting("column_porosity")   if get_setting("column_porosity")   is not None else DEFAULT_EPS
    except Exception:
        R_p, D_eff, eps_p, eps = DEFAULT_R_P, DEFAULT_D_EFF, DEFAULT_EPS_P, DEFAULT_EPS
    F_ratio = (1 - eps) / eps
    return R_p, D_eff, eps_p, F_ratio


def estimate_grm_init_params(decomposition, **kwargs):
    """
    Estimate GRM initial parameters from EGH component moments.

    Uses the LKM estimator for (Pe, t0, k_MT_i, R_i) then converts k_MT_i
    to k_ext_i via the Qamar 2014 moment-matching formula.

    Parameters
    ----------
    decomposition : Decomposition
        Decomposition whose ``xr_ccurves`` hold the component curves.
    R_p : float, optional
        Particle radius [cm].  Default from SerialSettings or 0.0035 cm.
    D_eff : float, optional
        Effective pore diffusivity [cm²/min].  Default 1e3 (film-only limit).
    eps_p : float, optional
        Intraparticle porosity.  Default 0.0 (non-porous).
    eps : float, optional
        Interstitial column porosity.  Default 0.4.
    debug : bool, optional
        Verbose output.

    Returns
    -------
    Pe : float
    t0 : float
    R_p : float
    D_eff : float
    a_star_list : list of float    eps_p + (1-eps_p)*a_henry   per component
    F_ratio : float     (1-eps)/eps                  (shared)
    k_ext_list : list of float    per component
    R_list : list of float        per component
    scale_list : list of float    per component
    """
    debug = kwargs.get('debug', False)

    from molass.SEC.Models.LkmEstimator import estimate_lkm_init_params
    Pe, t0, k_MT_list, R_list, scale_list = estimate_lkm_init_params(
        decomposition, **kwargs)

    R_p_def, D_eff_def, eps_p_def, F_def = _get_grm_column_settings()
    R_p     = kwargs.get('R_p',   R_p_def)
    D_eff   = kwargs.get('D_eff', D_eff_def)
    eps_p   = kwargs.get('eps_p', eps_p_def)
    eps     = kwargs.get('eps',   None)
    if eps is not None:
        F_ratio = (1 - eps) / eps
    else:
        F_ratio = F_def

    # a_star per component (R = 1 + F*a_star → a = (R-1)/F; a_star = eps_p + (1-eps_p)*a)
    # For non-porous particles (eps_p=0), a_star = a_henry.
    a_henry_list = [(R_i - 1) / F_ratio for R_i in R_list]
    a_star_list  = [eps_p + (1 - eps_p) * a for a in a_henry_list]

    # k_ext_i from k_MT_LKM via Qamar App C:
    #   k_MT_eff = k_MT_LKM * (R-1)/R
    #   k_ext    = k_MT_eff * R_p * R / (3*F) = k_MT_LKM * (R-1)*R_p / (3*F)
    k_ext_list = []
    for k_MT_i, R_i in zip(k_MT_list, R_list):
        k_ext_i = k_MT_i * (R_i - 1) * R_p / (3 * F_ratio)
        k_ext_list.append(max(k_ext_i, 1e-6))   # clamp to positive

    if debug:
        print(f"GRM estimator: Pe={Pe:.1f}  t0={t0:.2f}")
        print(f"  R_p={R_p}  D_eff={D_eff}  eps_p={eps_p}  F={F_ratio:.3f}")
        for i, (R_i, k_ext_i, scale_i, a_star_i) in enumerate(zip(R_list, k_ext_list, scale_list, a_star_list)):
            k_MT_eff = 3 * F_ratio * k_ext_i / (R_p * R_i)
            print(f"  comp {i}: R={R_i:.3f}  k_ext={k_ext_i:.5f}  "
                  f"k_MT_eff={k_MT_eff:.4f}  a_star={a_star_i:.4f}  scale={scale_i:.4f}")

    return Pe, t0, R_p, D_eff, a_star_list, F_ratio, k_ext_list, R_list, scale_list
