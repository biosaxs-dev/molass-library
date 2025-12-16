"""
Decompose.Partner.py
"""

import numpy as np
from scipy.optimize import minimize

def decompose_from_partner(icurve, mapping, xr_ccurves, debug=False):
    """
    Guess initial parameters for decomposition based on partner parameters.

    Parameters
    ----------
    icurve : Curve
        The intensity elution curve to be decomposed.
    mapping : MappingInfo
        The mapping information to convert partner parameters to current data parameters.
    xr_ccurves : list of ComponentCurve
        The list of XR component curves to extract partner parameters from.
    debug : bool, optional
        If True, enable debug mode, by default False.    

    Returns
    -------
    initial_params : array-like
        The guessed initial parameters for the egh function: (height, mean, std, tau).
    """
    from molass.SEC.Models.Simple import egh
    if debug:
        print("Decompose.Partner.decompose_from_partner: reload modules for debug")
        from importlib import reload
        import molass.SEC.Models.UvComponentCurve
        reload(molass.SEC.Models.UvComponentCurve)
    from molass.SEC.Models.UvComponentCurve import UvComponentCurve
    from molass.Mapping.Mapping import Mapping

    a, b = mapping.slope, mapping.intercept
    initial_params = []
    spline = icurve.get_spline()
    for ccurve in xr_ccurves:
        H_, tR_, sigma_, tau_ = ccurve.get_params()
        tR = tR_ * a + b
        H = spline(tR)
        sigma = sigma_ * a
        tau = tau_ * a
        params = np.array([H, tR, sigma, tau])
        initial_params.append(params)
 
    initial_params = np.array(initial_params)

    if debug:
        import matplotlib.pyplot as plt
        x, y = icurve.get_xy()
        fig, axes = plt.subplots(ncols=2, figsize=(12,5))
        fig.suptitle("Decompose from Partner")
        for title, ax, params in [("Initial Parameters", axes[0], initial_params),
                                  ("Optimized Parameters", axes[1], temp_params)]:
            ax.set_title(title)
            ax.plot(x, y, color='gray', alpha=0.5)
            for params in initial_params:
                ax.plot(x, egh(x, *params), linestyle=':')
        fig.tight_layout()
        plt.show()

    temp_params = initial_params.copy()

    x, y = icurve.get_xy()
    def objective(scales):
        temp_params[:,0] = scales
        y_fit = np.zeros_like(y)
        for p in temp_params:
            y_fit += egh(x, *p)
        return np.sum((y - y_fit)**2)

    result = minimize(objective, initial_params[:,0].ravel())
    temp_params[:,0] = result.x

    # uv_ccurves
    mapping_ = Mapping(a, b)    # task: make clear the difference between mapping and mapping_
    uv_ccurves = []
    for scale, xr_ccurve in zip(result.x, xr_ccurves):
        xr_h = xr_ccurve.get_params()[0]
        uv_ccurves.append(UvComponentCurve(x, mapping_, xr_ccurve, scale/xr_h))

    return uv_ccurves