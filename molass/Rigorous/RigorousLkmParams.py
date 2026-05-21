"""
Rigorous.RigorousLkmParams.py

Build the flat initial-params vector for G1400 (LKM rigorous optimizer)
from an LKM-model decomposition.

lkmcol_params layout: [Pe, t0, R_0, k_MT_0, R_1, k_MT_1, ..., R_{nc-1}, k_MT_{nc-1}]
"""
import numpy as np


def make_rigorous_initparams_impl(decomposition, baseparams, debug=False):
    """Build the flat init-params vector for G1400 from an LKM Decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        Decomposition whose ``xr_ccurves`` are ``LkmComponentCurve`` objects.
    baseparams : list
        ``[uv_baseparams, xr_baseparams]`` as returned by
        ``Decomposition.get_baseparams()``.
    debug : bool
        Passed through for optional debug output.

    Returns
    -------
    numpy.ndarray
        Flat parameter vector suitable for ``G1400.__init__``.
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
        print("LKM Rg params:", rg_params)

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

    # ── LKM column params: [Pe, t0, R_0, k_MT_0, R_1, k_MT_1, ...] ─────────
    ccurve0 = decomposition.xr_ccurves[0]
    Pe = ccurve0.Pe
    t0 = ccurve0.t0
    lkmcol_params = [Pe, t0]
    for ccurve in decomposition.xr_ccurves:
        lkmcol_params.append(ccurve.R)
        lkmcol_params.append(ccurve.k_MT)
    lkmcol_params = np.array(lkmcol_params)

    return np.concatenate([
        xr_params,
        xr_baseparams,
        rg_params,
        (a, b),
        uv_params,
        uv_baseparams,
        init_mappable_range,
        lkmcol_params,
    ])
