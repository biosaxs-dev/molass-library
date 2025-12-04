"""
LowRank.RigorousEghParams.py
"""
import os
import numpy as np
from importlib import reload

def make_rigorous_initparams_impl(decomposition, baseparams, debug=False):
    # Rg parameters
    orig_rg_params = decomposition.get_rgs()

    # XR initial parameters
    xr_params = []
    rg_params = []
    for ccurve in decomposition.xr_ccurves:
        xr_params.append(ccurve.scale)
        rg_params.append(ccurve.rg)
    xr_params = np.array(xr_params)
    rg_params = np.array(rg_params)
    print("Original Rg params:", orig_rg_params)
    print("SDM adjusted Rg params:", rg_params)

    # XR baseline parameters
    xr_baseparams = baseparams[1]

    # Mapping parameters
    a, b = decomposition.ssd.get_mapping()

    # UV initial parameters
    uv_params = []
    for uv_ccurve in decomposition.uv_ccurves:
        uv_params.append(uv_ccurve.scale)
    uv_params = np.array(uv_params) * xr_params

    # UV baseline parameters
    uv_baseparams = baseparams[0]

    # SecCol parameters
    x = decomposition.ssd.xr.get_icurve().x
    init_mappable_range = (x[0], x[-1])

    # SecCol parameters
    column = decomposition.xr_ccurves[0].column
    N, T, me, mp, x0, tI, N0, poresize, timescale = column.get_params()
    K = N*T
    sdmcol_params = np.array([N, K, x0, poresize, N0, tI])
    return np.concatenate([xr_params, xr_baseparams, rg_params, (a, b), uv_params, uv_baseparams, init_mappable_range, sdmcol_params])