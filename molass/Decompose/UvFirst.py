"""
Decompose.UvFirst.py

UV-first proportional decomposition: fits the full proportional decomposition on the UV
icurve -- which usually has much better signal-to-noise than XR for small features (e.g.
shoulders next to a dominant peak) -- and derives XR component curves by mapping the
fitted UV shape onto the XR frame axis and refitting only the per-component heights
against the real XR data.

This is the mirror image of the default (and still primary) XR-first flow --
see molass.Decompose.Proportional.decompose_proportionally() and
molass.Decompose.Partner.decompose_from_partner() -- kept as an explicit, opt-in
alternative (``proportions_source='uv'`` in quick_decomposition()) rather than folded
into the default path, since XR remains the canonical shape source for the rest of the
pipeline (LRF, Rg/Guinier analysis, rigorous optimization).
"""
from molass.Decompose.Proportional import decompose_proportionally
from molass.Decompose.Partner import decompose_from_partner, map_params_to_partner
from molass.LowRank.ComponentCurve import ComponentCurve


def make_component_curves_with_uv_proportions(ssd, num_components, proportions, debug=False,
                                               allow_negative_peaks=False, num_plates=None):
    """
    Decompose proportionally on the UV icurve first, then derive XR component curves by
    mapping the fitted UV shape onto the XR frame axis and refitting only the heights.

    Parameters
    ----------
    ssd : SecSaxsData
        The SecSaxsData object containing the data.
    num_components : int
        The number of components to decompose into.
    proportions : list of float
        The proportions for each component (interpreted against the UV icurve's area).
    debug : bool, optional
        If True, enable debug mode to visualize the decomposition process. Default False.
    allow_negative_peaks : bool, optional
        If True, allow negative peak heights (H < 0). Default False.
    num_plates : int, optional
        Extra plate-count candidate for the UV fit's Stage 2 grid search -- see
        decompose_proportionally(). Default None.

    Returns
    -------
    xr_icurve, xr_ccurves, uv_icurve, uv_ccurves
        Same shape as molass.LowRank.QuickImplement.make_component_curves_with_proportions().
    """
    uv_icurve = ssd.uv.get_icurve()
    xr_icurve = ssd.xr.get_icurve()
    mapping = ssd.get_mapping()

    uv_result = decompose_proportionally(uv_icurve, proportions, debug=debug,
                                          allow_negative_peaks=allow_negative_peaks, num_plates=num_plates)
    uv_classic_params = uv_result.x.reshape(num_components, 4)

    _, xr_classic_params = map_params_to_partner(xr_icurve, mapping, uv_classic_params, direction='uv_to_xr')
    xr_ccurves = [ComponentCurve(xr_icurve.x, params) for params in xr_classic_params]

    # rebuild UvComponentCurve tied to the new xr_ccurves -- required by the rest of the
    # pipeline (LRF, scoring, rigorous optimization all assume uv_ccurves[i] references an
    # xr_ccurve); since the shape originated from the UV fit itself, this should closely
    # reproduce uv_result, modulo the XR height refit's influence on the reported ratio.
    uv_ccurves = decompose_from_partner(uv_icurve, mapping, xr_ccurves, debug=debug)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves
