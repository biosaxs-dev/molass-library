"""
LowRank.QuickImplement
"""
from importlib import reload

def make_decomposition_impl(ssd, num_components=None, **kwargs):    
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.CoupledAdjuster
        reload(molass.LowRank.CoupledAdjuster)
    from molass.LowRank.CoupledAdjuster import make_component_curves

    xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves(ssd, num_components, **kwargs)

    if debug:
        import molass.LowRank.Decomposition
        reload(molass.LowRank.Decomposition)
    from molass.LowRank.Decomposition import Decomposition

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)