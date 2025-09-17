"""
LowRank.PositionedDecomposer.py

This module contains the functions to decompose a curve according to
specified peak positions.
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
from scipy.optimize import minimize
from molass.SEC.Models.Simple import egh

def decompose_icurve_positioned(x, y, decompargs, **kwargs):
    debug = kwargs.get('debug', False)
    peakpositions = decompargs.get('peakpositions', [])
    if len(peakpositions) == 0:
        raise ValueError("No peak positions specified.")
    tau_limit = decompargs.get('tau_limit', 0.6)
    max_sigma = decompargs.get('max_sigma', 17)
    spline = UnivariateSpline(x, y, s=0, ext=3)
    init_params_list = []
    for k, px in enumerate(peakpositions):
        print([k], px)
        h = spline(px)
        init_params_list.append((h, px, 20, 0))
    
    shape = (len(peakpositions), 4)

    def fit_func(p, debug=False):
        cy_list = []
        dev_penalty = 0
        min_penalty = 0
        tau_penalty = 0
        sig_penalty = 0
        for k, (h, m, s, t) in enumerate(p.reshape(shape)):
            cy = egh(x, h, m, s, t)
            dev_penalty += (m - peakpositions[k])**2
            min_penalty += min(0, h - 0.02)**2
            tau_penalty += max(0, t/s - tau_limit)**2
            sig_penalty += max(0, s - max_sigma)**2
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        if debug:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.plot(x, y)
            for k, cy in enumerate(cy_list):
                ax.plot(x, cy, ":")
            ax.plot(x, ty, ":", color='red')
            plt.show()
        return np.sum((ty - y)**2) + 1000 * (dev_penalty + min_penalty + tau_penalty + sig_penalty)

    res = minimize(fit_func, np.array(init_params_list).flatten(), method='Nelder-Mead')
    if debug:
        fit_func(res.x, debug=True)

    return res.x.reshape(shape)


