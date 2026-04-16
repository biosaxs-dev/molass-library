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
    sdmcol = separated_params[-1]
    # Infer pore_dist/rt_dist from function code
    func_code = getattr(optimizer, 'function_code', None)
    me = mp = 1.5
    if func_code == 'G1300':
        # Lognormal pore + gamma: sdmcol = [N, K, x0, mu, sigma, N0, tI, k]
        N, K, x0, mu, sigma, N0, tI, k_gamma = sdmcol
        T = K/N
        column = SdmColumn([N, T, me, mp, x0, tI, N0, mu, sigma, k_gamma],
                           pore_dist='lognormal', rt_dist='gamma')
    else:
        if len(sdmcol) >= 7:
            N, K, x0, poresize, N0, tI, k_gamma = sdmcol[:7]
        else:
            N, K, x0, poresize, N0, tI = sdmcol
            k_gamma = 1.0
        T = K/N
        if func_code == 'G1200':
            pore_dist, rt_dist = 'mono', 'gamma'
        elif k_gamma != 1.0:
            pore_dist, rt_dist = 'mono', 'gamma'
        else:
            pore_dist, rt_dist = 'mono', 'exponential'
        column = SdmColumn([N, T, me, mp, x0, tI, N0, poresize, DEFUALT_TIMESCALE, k_gamma],
                           pore_dist=pore_dist, rt_dist=rt_dist)
    x = xr_icurve.x
    xr_ccurves = []
    for scale, rg in zip(xr_params, rg_params):
        xr_ccurves.append(SdmComponentCurve(x, column, rg, scale))
    return xr_ccurves

def get_edm_xr_ccurves(optimizer, xr_icurve, separated_params):
    from molass.SEC.Models.EdmComponentCurve import EdmComponentCurve
    xr_params = separated_params[0]  # shape (num_components, 7): (t0, u, a, b, e, Dz, cinj) per component
    x = xr_icurve.x
    xr_ccurves = []
    for p in xr_params:
        xr_ccurves.append(EdmComponentCurve(x, p))
    return xr_ccurves

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