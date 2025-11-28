"""
    LowRank.LowRankInfo.py
"""
import numpy as np
    
def make_egh_initparams(decomposition, base_curves, debug=False):
    """
    Make initial parameters for rigorous optimization.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition object containing the components.
    base_curves : list of Curve
        The base curves for XR and UV data.
    debug : bool, optional
        If True, enable debug mode.

    Returns
    -------
    np.ndarray
        The initial parameters for rigorous optimization.
    """
    if debug:
        from importlib import reload
        import molass.Rigorous.EghParams
        reload(molass.Rigorous.EghParams)
    from molass.Rigorous.EghParams import make_egh_initparams

    # XR initial parameters
    xr_params = []
    for ccurve in decomposition.xr_ccurves:
        xr_params.append(ccurve.get_params())
    xr_params = np.array(xr_params)
    # XR baseline parameters
    xr_baseparams = base_curves[0].get_params()

    # Rg parameters
    rg_params = decomposition.get_rgs()

    # Mapping parameters
    a, b = decomposition.ssd.get_mapping()

    # UV initial parameters
    uv_params = []
    for uv_ccurve, xr_ccurve in zip(decomposition.uv_ccurves, decomposition.xr_ccurves):
        uv_params.append(uv_ccurve.get_params()[0]/xr_ccurve.get_params()[0])

    # UV baseline parameters
    uv_baseparams = base_curves[1].get_params()

    # SecCol parameters
    x = decomposition.ssd.xr_icurve.x
    init_mappable_range = (x[0], x[-1])

    # SecCol parameters
    from molass_legacy.SecTheory.SecEstimator import guess_initial_secparams
    Npc, rp, tI, t0, P, m = guess_initial_secparams(xr_params, rg_params)
    seccol_params = np.array([Npc, rp, tI, t0, P, m])

    return np.concatenate([xr_params.flatten(),
                           xr_baseparams,
                           rg_params,
                           uv_params,
                           uv_baseparams,
                           init_mappable_range,
                           seccol_params])
