"""
Decompose.Partner.py
"""

import numpy as np
from scipy.optimize import minimize

def decompose_from_partner(icurve, mapping, partner_params, debug=False):
    """
    Guess initial parameters for decomposition based on partner parameters.

    Parameters
    ----------
    icurve : Curve
        The intensity elution curve to be decomposed.
    mapping : MappingInfo
        The mapping information to convert partner parameters to current data parameters.
    partner_params : OptimizeResult.x
        The optimized parameters from the partner data.
    debug : bool, optional
        If True, enable debug mode, by default False.    

    Returns
    -------
    initial_params : array-like
        The guessed initial parameters for the egh function: (height, mean, std, tau).
    """
    from molass.SEC.Models.Simple import egh

    a, b = mapping.slope, mapping.intercept
    initial_params = []
    spline = icurve.get_spline()
    for H_, tR_, sigma_, tau_ in partner_params.reshape((-1, 4)):
        tR = tR_ * a + b
        H = spline(tR)
        sigma = sigma_ * a
        tau = tau_ * a
        params = np.array([H, tR, sigma, tau])
        initial_params.append(params)
 
    initial_params = np.array(initial_params)

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

    return dict(x=temp_params)