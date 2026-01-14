"""
Rigorous.ComponentUtils.py
"""

def get_egh_xr_ccurves(optimizer, xr_icurve, separated_params):
    from molass.LowRank.ComponentCurve import ComponentCurve
    xr_params = separated_params[0]
    x = xr_icurve.x
    xr_ccurves = []
    for p in xr_params:
        xr_ccurves.append(ComponentCurve(x, p))
    return xr_ccurves

def get_sdm_xr_ccurves(optimizer, xr_icurve, separated_params):
    from molass_legacy.Models.Stochastic.DispersivePdf import DEFUALT_TIMESCALE
    from molass.SEC.Models.SdmComponentCurve import SdmColumn, SdmComponentCurve
    xr_params = separated_params[0]
    rg_params = separated_params[2]
    N, K, x0, poresize, N0, tI = separated_params[-1]
    T = K/N
    me = mp = 1.5
    column = SdmColumn([N, T, me, mp, x0, tI, N0, poresize, DEFUALT_TIMESCALE])
    x = xr_icurve.x
    xr_ccurves = []
    for scale, rg in zip(xr_params, rg_params):
        xr_ccurves.append(SdmComponentCurve(x, column, rg, scale))
    return xr_ccurves

def get_edm_xr_ccurves(optimizer, xr_icurve, separated_params):
    raise NotImplementedError("EDM XR component curve extraction not implemented yet.")

def get_xr_ccurves(optimizer, xr_icurve, separated_params):
    model_name = optimizer.get_model_name()
    if model_name == 'EGH':
        return get_egh_xr_ccurves(optimizer, xr_icurve, separated_params)
    elif model_name == 'SDM':
        return get_sdm_xr_ccurves(optimizer, xr_icurve, separated_params)
    elif model_name == 'EDM':
        return get_edm_xr_ccurves(optimizer, xr_icurve, separated_params)
    else:
        raise ValueError(f"Unknown model_name: {model_name}")