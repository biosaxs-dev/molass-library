"""
LowRank.QuickImplement
"""
import numpy as np
from importlib import reload

def make_decomposition_impl(ssd, num_components=None, **kwargs):    
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.CoupledAdjuster
        reload(molass.LowRank.CoupledAdjuster)
    from molass.LowRank.CoupledAdjuster import make_component_curves

    proportions = kwargs.pop('proportions', None)
    if proportions is None:
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves(ssd, num_components, **kwargs)
    else:
        if num_components is None:
            num_components = len(proportions)
        else:
            assert num_components == len(proportions), "num_components must be equal to the length of proportions."
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves_with_proportions(ssd, num_components, proportions, **kwargs)

    if debug:
        import molass.LowRank.Decomposition
        reload(molass.LowRank.Decomposition)
    from molass.LowRank.Decomposition import Decomposition

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)

def make_component_curves_with_proportions(ssd, num_components, proportions, **kwargs):
    """
    Make component curves with given proportions.
    """

    assert len(proportions) == num_components, "Length of proportions must be equal to num_components."
    proportions = np.asarray(proportions)
    assert np.all(proportions >= 0), "All proportions must be non-negative."
    assert np.sum(proportions) > 0, "Sum of proportions must be positive."
    proportions = proportions/np.sum(proportions)
    xr_icurve = ssd.xr.get_icurve()
    xr_ccurves = create_decomposition_from_params(xr_icurve, num_components, proportions, **kwargs)
    uv_icurve = ssd.uv.get_icurve()
    uv_ccurves = create_decomposition_from_params(uv_icurve, num_components, proportions, **kwargs)
    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves

def create_decomposition_from_params(icurve, num_components, proportions, **kwargs):
    debug = kwargs.get('debug', False)
    if debug:
        import molass.Decompose.Proportional
        reload(molass.Decompose.Proportional)
    from molass.Decompose.Proportional import decompose_proportionally

    from molass.LowRank.ComponentCurve import ComponentCurve
    
    x, y = icurve.get_xy()
    result = decompose_proportionally(x, y, proportions, debug=debug)

    ret_curves = []
    for params in result.x.reshape((num_components, 4)):
        ret_curves.append(ComponentCurve(x, params))
    return ret_curves