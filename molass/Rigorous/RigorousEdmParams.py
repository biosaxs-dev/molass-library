"""
Rigorous.RigorousEdmParams.py

Builds the G2020 (EDM) initial parameter vector from an EDM Decomposition.

The EDM parameter layout is:
    [a_0, b_0, cinj_0, a_1, b_1, cinj_1, ...]   <- xr_params (nc × 3, flattened)
    xr_baseparams
    rg_params (nc)
    mapping (a_mp, b_mp)
    uv_params (nc)
    uv_baseparams (5 + num_baseparams)
    mappable_range (c, d)
    t0_sh, u_sh, e_sh, Dz_sh                     <- edm_colparams (4)
"""
import numpy as np


def make_rigorous_initparams_impl(decomposition, baseparams, debug=False):
    # Extract the shared column params from the first component curve.
    # EdmComponentCurve.params order: (t0, u, a, b, e, Dz, cinj)
    p0 = decomposition.xr_ccurves[0].params
    t0_sh, u_sh = p0[0], p0[1]
    e_sh, Dz_sh = p0[4], p0[5]

    # Per-component (a, b, cinj)
    xr_abc = []
    for ccurve in decomposition.xr_ccurves:
        t0, u, a, b, e, Dz, cinj = ccurve.params
        xr_abc.append((a, b, cinj))
    xr_abc = np.array(xr_abc)            # shape (nc, 3)

    # XR baseline parameters
    xr_baseparams = baseparams[1]

    # Rg parameters
    rg_params = decomposition.get_rgs()

    # UV/XR mapping
    a_mp, b_mp = decomposition.ssd.get_mapping()

    # UV heights
    uv_params = np.array([uv_ccurve.scale for uv_ccurve in decomposition.uv_ccurves])

    # UV baseline parameters
    uv_baseparams = baseparams[0]

    # Mappable range
    x = decomposition.ssd.xr.get_icurve().x
    init_mappable_range = (x[0], x[-1])

    # Shared column params (appended at the end)
    edm_colparams = np.array([t0_sh, u_sh, e_sh, Dz_sh])

    if debug:
        print("RigorousEdmParams: xr_abc =", xr_abc)
        print("RigorousEdmParams: edm_colparams =", edm_colparams)

    return np.concatenate([
        xr_abc.flatten(), xr_baseparams, rg_params,
        (a_mp, b_mp), uv_params, uv_baseparams,
        init_mappable_range, edm_colparams
    ])
