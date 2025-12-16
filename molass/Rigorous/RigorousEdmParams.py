"""
LowRank.RigorousEghParams.py
"""
import os
import numpy as np
from importlib import reload

def make_rigorous_initparams_impl(decomposition, baseparams, debug=False):
    # XR initial parameters
    xr_params = []
    for ccurve in decomposition.xr_ccurves:
        xr_params.append(ccurve.get_params())
    xr_params = np.array(xr_params)
    # XR baseline parameters
    xr_baseparams = baseparams[1]

    # Rg parameters
    rg_params = decomposition.get_rgs()

    # Mapping parameters
    a, b = decomposition.ssd.get_mapping()

    # UV initial parameters
    uv_params = []
    for uv_ccurve in decomposition.uv_ccurves:
        uv_params.append(uv_ccurve.scale)

    # UV baseline parameters
    uv_baseparams = baseparams[0]

    # SecCol parameters
    x = decomposition.ssd.xr.get_icurve().x
    init_mappable_range = (x[0], x[-1])

    # SecCol parameters
    Tz = np.average(xr_params[:,0])     # not used
    return np.concatenate([xr_params.flatten(), xr_baseparams, rg_params, (a, b), uv_params, uv_baseparams, init_mappable_range, [Tz]])
