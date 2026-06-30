"""
Rigorous.RigorousGrmParams.py

Build the flat initial-params vector for G1500 (GRM rigorous optimizer)
from a GRM-model decomposition.

grmcol_params layout:
  [Pe, t0, R_p, D_eff, R_0, k_ext_0, R_1, k_ext_1, ..., R_{nc-1}, k_ext_{nc-1}]
  Total length: 4 + 2*nc
"""
import numpy as np


def make_rigorous_initparams_impl(decomposition, baseparams, debug=False):
    """Build the flat init-params vector for G1500 from a GRM Decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        Decomposition whose ``xr_ccurves`` are ``GrmComponentCurve`` objects.
    baseparams : list
        ``[uv_baseparams, xr_baseparams]`` as returned by
        ``Decomposition.get_baseparams()``.
    debug : bool
        Passed through for optional debug output.

    Returns
    -------
    numpy.ndarray
        Flat parameter vector suitable for ``G1500.__init__``.
    """
    # ── Rg (for diagnostics) ─────────────────────────────────────────────────
    orig_rg_params = decomposition.get_rgs()

    # ── XR component scales and Rg ─────────────────────────────────────────
    xr_params = []
    rg_params = []
    for ccurve in decomposition.xr_ccurves:
        xr_params.append(ccurve.scale)
        rg = getattr(ccurve, 'rg', None)
        rg_params.append(rg if (rg is not None and not np.isnan(rg)) else 30.0)
    xr_params = np.array(xr_params)
    rg_params  = np.array(rg_params)
    if debug:
        print("Original Rg params:", orig_rg_params)
        print("GRM Rg params:", rg_params)

    # ── XR baseline ──────────────────────────────────────────────────────────
    xr_baseparams = baseparams[1]

    # ── UV/XR mapping ────────────────────────────────────────────────────────
    a, b = decomposition.ssd.get_mapping()

    # ── UV component scales (scaled to XR) ───────────────────────────────────
    uv_params = []
    for uv_ccurve in decomposition.uv_ccurves:
        uv_params.append(uv_ccurve.scale)
    uv_params = np.array(uv_params) * xr_params

    # ── UV baseline ──────────────────────────────────────────────────────────
    uv_baseparams = baseparams[0]

    # ── Mappable range ───────────────────────────────────────────────────────
    x = decomposition.ssd.xr.get_icurve().x
    init_mappable_range = (x[0], x[-1])

    # ── GRM column params: [Pe, t0, R_p, D_eff, R_0, k_ext_0, R_1, k_ext_1, ...] ─
    ccurve0 = decomposition.xr_ccurves[0]
    Pe    = ccurve0.Pe
    t0    = ccurve0.t0
    R_p   = ccurve0.R_p
    D_eff = ccurve0.D_eff
    grmcol_params = [Pe, t0, R_p, D_eff]
    for ccurve in decomposition.xr_ccurves:
        grmcol_params.append(ccurve.R)
        grmcol_params.append(ccurve.k_ext)
    grmcol_params = np.array(grmcol_params)

    if debug:
        print("GRM col params (Pe, t0, R_p, D_eff, R_0, k_ext_0, ...):", grmcol_params)

    return np.concatenate([
        xr_params,
        xr_baseparams,
        rg_params,
        (a, b),
        uv_params,
        uv_baseparams,
        init_mappable_range,
        grmcol_params,
    ])
