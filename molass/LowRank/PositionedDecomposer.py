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
    """ Decompose the given curve (x, y) into a sum of exponentially
    modified Gaussian (EMG) functions, with peak positions specified
    in decompargs['peakpositions'].

    Parameters
    ----------
    x : np.ndarray
        The x values of the curve.
    y : np.ndarray
        The y values of the curve.
    decompargs : dict
        A dictionary containing decomposition arguments. Must include
        'peakpositions', a list of peak positions.
    debug : bool, optional
        If True, enables debug mode with additional output.
        
    Returns
    -------
    params : np.ndarray
        A 2D array of shape (number of peaks, 4), where each row contains
        the parameters (height, mean, sigma, tau) of the corresponding EMG function.
    """
    debug = kwargs.get('debug', False)
    peakpositions = decompargs.get('peakpositions', [])
    if len(peakpositions) == 0:
        raise ValueError("No peak positions specified.")
    tau_limit = decompargs.get('tau_limit', 0.6)
    max_sigma = decompargs.get('max_sigma', 17)
    min_sigma = decompargs.get('min_sigma', 5)
    spline = UnivariateSpline(x, y, s=0, ext=3)

    # Estimate initial sigma from half-distance to nearest neighbor
    sorted_px = np.sort(peakpositions)
    init_params_list = []
    for k, px in enumerate(peakpositions):
        h = float(spline(px))
        idx = np.searchsorted(sorted_px, px)
        neighbors = []
        if idx > 0:
            neighbors.append(sorted_px[idx] - sorted_px[idx - 1])
        if idx < len(sorted_px) - 1:
            neighbors.append(sorted_px[idx + 1] - sorted_px[idx])
        sigma_est = max(min_sigma, min(neighbors) / 3) if neighbors else 20
        init_params_list.append((h, px, sigma_est, 0))
    
    shape = (len(peakpositions), 4)

    def fit_func(p, debug=False):
        cy_list = []
        dev_penalty = 0
        min_penalty = 0
        tau_penalty = 0
        sig_penalty = 0
        for k, (h, m, s, t) in enumerate(p.reshape(shape)):
            abs_s = abs(s) + 1e-6  # enforce positive sigma
            cy = egh(x, h, m, abs_s, t)
            dev_penalty += (m - peakpositions[k])**2
            min_penalty += min(0, h)**2
            tau_penalty += max(0, abs(t)/abs_s - tau_limit)**2
            sig_penalty += max(0, abs_s - max_sigma)**2 + max(0, min_sigma - abs_s)**2
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

    res = minimize(fit_func, np.array(init_params_list).flatten(), method='Nelder-Mead',
                   options={'maxiter': 10000 * len(peakpositions), 'xatol': 1e-6, 'fatol': 1e-8})
    if debug:
        fit_func(res.x, debug=True)

    result = res.x.reshape(shape)
    result[:, 2] = np.abs(result[:, 2]) + 1e-6  # ensure positive sigma
    return result


