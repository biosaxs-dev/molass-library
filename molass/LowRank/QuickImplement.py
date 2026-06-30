"""
LowRank.QuickImplement
"""
import numpy as np
from importlib import reload
from molass.Decompose.XrOnlyUtils import make_dummy_uv_ccurves

def make_decomposition_impl(ssd, num_components=None, **kwargs):    
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.CoupledAdjuster
        reload(molass.LowRank.CoupledAdjuster)
    from molass.LowRank.CoupledAdjuster import make_component_curves

    proportions = kwargs.pop('proportions', None)
    xr_peakpositions = kwargs.pop('xr_peakpositions', None)
    if proportions is not None and xr_peakpositions is not None:
        raise ValueError("Cannot specify both 'proportions' and 'xr_peakpositions'.")

    if xr_peakpositions is not None:
        if num_components is None:
            num_components = len(xr_peakpositions)
        else:
            assert num_components == len(xr_peakpositions), "num_components must equal len(xr_peakpositions)."
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves_with_positions(ssd, num_components, xr_peakpositions, **kwargs)
    elif proportions is not None:
        if num_components is None:
            num_components = len(proportions)
        else:
            assert num_components == len(proportions), "num_components must be equal to the length of proportions."
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves_with_proportions(ssd, num_components, proportions, **kwargs)
    else:
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves(ssd, num_components, **kwargs)

    if debug:
        import molass.LowRank.Decomposition
        reload(molass.LowRank.Decomposition)
    from molass.LowRank.Decomposition import Decomposition

    if len(xr_ccurves) == 0:
        raise ValueError(
            "Auto-detection found 0 components. The data may have insufficient signal. "
            "Try specifying num_components explicitly."
        )

    if uv_ccurves is None:
        uv_ccurves = make_dummy_uv_ccurves(ssd, xr_ccurves)

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
    allow_negative = kwargs.get('allow_negative_peaks', False)
    xr_result = decompose_proportionally(xr_icurve, proportions, debug=debug, allow_negative_peaks=allow_negative)
    xr_ccurves = get_curves_from_params(xr_result.x, xr_icurve)

    # Create UV curves
    if ssd.has_uv():
        uv_icurve = ssd.uv.get_icurve()
        mapping = ssd.get_mapping()
        uv_ccurves = decompose_from_partner(uv_icurve, mapping, xr_ccurves, debug=debug)
    else:
        uv_icurve = None
        uv_ccurves = make_dummy_uv_ccurves(ssd, xr_ccurves)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves

def make_component_curves_with_positions(ssd, num_components, xr_peakpositions, **kwargs):
    """
    Make component curves with peak positions pinned to specified frame numbers.

    Parameters
    ----------
    ssd : SecSaxsData
        The SecSaxsData object containing the data.
    num_components : int
        The number of components to decompose into.
    xr_peakpositions : list of float
        The frame positions for each peak.
    """
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.PositionedDecomposer
        reload(molass.LowRank.PositionedDecomposer)
        import molass.Decompose.Partner
        reload(molass.Decompose.Partner)
    from molass.LowRank.PositionedDecomposer import decompose_icurve_positioned
    from molass.Decompose.Partner import decompose_from_partner
    from molass.LowRank.ComponentCurve import ComponentCurve

    decompargs = {
        'peakpositions': list(xr_peakpositions),
        'tau_limit': kwargs.pop('tau_limit', 0.6),
        'max_sigma': kwargs.pop('max_sigma', 80),
        'min_sigma': kwargs.pop('min_sigma', 5),
    }

    # Create XR curves
    xr_icurve = ssd.xr.get_icurve()
    x, y = xr_icurve.get_xy()
    params = decompose_icurve_positioned(x, y, decompargs, debug=debug)
    xr_ccurves = [ComponentCurve(xr_icurve.x, params[i]) for i in range(num_components)]

    # Create UV curves
    if ssd.has_uv():
        uv_icurve = ssd.uv.get_icurve()
        mapping = ssd.get_mapping()
        uv_ccurves = decompose_from_partner(uv_icurve, mapping, xr_ccurves, debug=debug)
    else:
        uv_icurve = None
        uv_ccurves = make_dummy_uv_ccurves(ssd, xr_ccurves)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves
