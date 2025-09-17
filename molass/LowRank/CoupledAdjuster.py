"""
    LowRank.CoupledAdjuster.py
"""

import numpy as np

def make_component_curves(ssd, num_components, **kwargs):
    """
    Make a LowRankInfo object.
    """
    ip_effect_info = kwargs.get('ip_effect_info', None)
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.LowRank.CurveDecomposer
        reload(molass.LowRank.CurveDecomposer)
    from molass.LowRank.CurveDecomposer import decompose_icurve_impl

    xr_peakpositions = kwargs.pop('xr_peakpositions', None)
    xr_icurve = ssd.xr.get_icurve()
    if num_components is None:
        num_components = len(xr_icurve.get_peaks())
    kwargs['data_matrix'] = ssd.xr.M
    kwargs['qv'] = ssd.xr.qv
    xr_ccurves = decompose_icurve_impl(xr_icurve, num_components, peakpositions=xr_peakpositions, **kwargs)

    uv_icurve = ssd.uv.get_icurve()

    smooth_uv = kwargs.get('smooth_uv', False)
    if smooth_uv:
        uv_icurve = uv_icurve.smooth_copy()
    if xr_peakpositions is None:
        uv_peakpositions = None
    else:
        mapping = ssd.estimate_mapping()
        uv_peakpositions = mapping.get_mapped_x(xr_peakpositions)
    uv_ccurves = decompose_icurve_impl(uv_icurve, num_components, peakpositions=uv_peakpositions, **kwargs)

    xr_ccurves, uv_ccurves = select_components(ssd, xr_ccurves, uv_ccurves)

    consistent_uv = kwargs.get('consistent_uv', True)
    if debug:
        print("consistent_uv=", consistent_uv)
    if consistent_uv:
        if debug:
            import molass.LowRank.ConsistentAdjuster
            reload(molass.LowRank.ConsistentAdjuster)
        from molass.LowRank.ConsistentAdjuster import adjust_components_consistently
        if ssd.mapping is None:
            ssd.estimate_mapping()
        uv_ccurves = adjust_components_consistently(ssd.mapping, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves

def select_components(ssd, xr_ccurves, uv_ccurves):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning('developer memo: remember that "LowRank.CoupledAdjuster.select_components" is not implemented yet.')
    return xr_ccurves, uv_ccurves