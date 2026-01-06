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

    if uv_ccurves is None:
        # temporary work-around for the case without UV data
        from molass.SEC.Models.UvComponentCurve import UvComponentCurve
        mapping = ssd.get_mapping()
        uv_ccurves = [UvComponentCurve(xr_ccurve.x, mapping, xr_ccurve, 1) for xr_ccurve in xr_ccurves]

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)

def make_component_curves_with_proportions(ssd, num_components, proportions, **kwargs):
    """
    Make component curves with given proportions.

    Parameters
    ----------
    ssd : SecSaxsData
        The SecSaxsData object containing the data.
    num_components : int
        The number of components to decompose into.
    proportions : list of float
        The proportions for each component.
    """

    assert len(proportions) == num_components, "Length of proportions must be equal to num_components."
    proportions = np.asarray(proportions)
    assert np.all(proportions >= 0), "All proportions must be non-negative."
    assert np.sum(proportions) > 0, "Sum of proportions must be positive."
    proportions = proportions/np.sum(proportions)

    debug = kwargs.get('debug', False)
    if debug:
        import molass.Decompose.Proportional
        reload(molass.Decompose.Proportional)
        import molass.Decompose.Partner
        reload(molass.Decompose.Partner)
    from molass.Decompose.Proportional import decompose_proportionally
    from molass.Decompose.Partner import decompose_from_partner
    from molass.LowRank.ComponentCurve import ComponentCurve

    def get_curves_from_params(result_params, icurve):
        ret_curves = []
        for params in result_params.reshape((num_components, 4)):
            ret_curves.append(ComponentCurve(icurve.x, params))
        return ret_curves

    # Create XR curves
    xr_icurve = ssd.xr.get_icurve()
    xr_result = decompose_proportionally(xr_icurve, proportions, debug=debug)
    xr_ccurves = get_curves_from_params(xr_result.x, xr_icurve)

    # Create UV curves
    uv_icurve = ssd.uv.get_icurve()
    mapping = ssd.get_mapping()
    uv_ccurves = decompose_from_partner(uv_icurve, mapping, xr_ccurves, debug=debug)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves
