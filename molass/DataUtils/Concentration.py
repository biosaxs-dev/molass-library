"""
    DataUtils.Consentration.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
class ConcInfo:
    def __init__(self, curve):
        self.curve = curve

def make_concinfo_impl(ssd, mapping, **kwargs):
    debug = kwargs.get('debug', False)

    concfactor = kwargs.get('concfactor', None)
    if concfactor is None:
        concfactor = ssd.get_concfactor()

    if mapping is None:
        mapping = ssd.estimate_mapping()

    if debug:
        print("make_concinfo_impl: concfactor=", concfactor)

    if concfactor is None:
        from molass.Except.ExceptionTypes import NotSpecifedError
        raise NotSpecifedError("concfactor is not given as a kwarg nor acquired from a UV file.")

    if ssd.uv is None:
        ssd.logger.warning("using XR data as concentration.")
        conc_curve = ssd.xr.get_icurve()
    else:
        if mapping is None:
            mapping = ssd.estimate_mapping()
        xr_curve = ssd.xr.get_icurve()
        uv_curve = ssd.uv.get_icurve()
        conc_curve = mapping.get_mapped_curve(xr_curve.x, uv_curve)

    return ConcInfo(conc_curve*concfactor)