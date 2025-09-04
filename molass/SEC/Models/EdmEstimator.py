"""
SEC.Models.EdmEstimator.py
"""
import numpy as np
from scipy.optimize import minimize

def estimate_edm_init_params(decomposition, **kwargs):
    """
    Estimate column parameters from the initial curve and component curves.

    N, T, N0, t0, poresize
    """
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.EdmEstimatorImpl
        reload(molass.SEC.Models.EdmEstimatorImpl)
    from molass.SEC.Models.EdmEstimatorImpl import guess_multiple_impl

    xr_icurve = decomposition.xr_icurve
    x, y = xr_icurve.get_xy()
    xr_params = guess_multiple_impl(x, y, decomposition.xr_ccurves, debug=debug)
    return xr_params