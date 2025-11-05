"""
LowRank.RigorousImplement
"""
import numpy as np
from importlib import reload

def make_rigorous_decomposition_impl(decomposition, rgcurve, debug=False):
    """
    Make a rigorous decomposition using a given RG curve.

    Parameters
    ----------
    decomposition : Decomposition
        The initial decomposition to refine.
    rgcurve : RgComponentCurve
        The Rg component curve to use for refinement.
    debug : bool, optional
        If True, enable debug mode with additional output.

    Returns
    -------
    Decomposition
        The refined decomposition object.
    """
    if debug:
        import molass.LowRank.Decomposition
        reload(molass.LowRank.Decomposition)
    from molass.LowRank.Decomposition import Decomposition

    ssd = decomposition.ssd
    xr_icurve = decomposition.xr_icurve
    uv_icurve = decomposition.uv_icurve
    xr_ccurves = decomposition.xr_ccurves
    uv_ccurves = decomposition.uv_ccurves

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves)