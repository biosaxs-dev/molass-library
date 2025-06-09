"""
    LowRank.CurveDecomposer.py

    This module contains the decompose functions used to decompose
    a given I-curve into a set of component curves.
"""
from importlib import reload
import numpy as np
from scipy.optimize import minimize
from molass_legacy.QuickAnalysis.ModeledPeaks import recognize_peaks
from molass_legacy.Models.ElutionCurveModels import egh

TAU_PENALTY_SCALE = 1000

def compute_areas(x, peak_list):
    areas = []
    for params in peak_list:
        y = egh(x, *params)
        areas.append(np.sum(y))
    return np.array(areas)

def decompose_icurve_impl(icurve, num_components, **kwargs):
    """
    Decompose a curve into component curves.
    """
    from molass.LowRank.ComponentCurve import ComponentCurve

    elution_model = kwargs.get('elution_model', 'egh')
    smoothing = kwargs.get('smoothing', False)
    debug = kwargs.get('debug', False)

    x, y = icurve.get_xy()

    if smoothing:
        from molass_legacy.KekLib.SciPyCookbook import smooth
        sy = smooth(y)
        if debug:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.set_title("decompose_icurve_impl debug")
            ax.plot(x, y)
            ax.plot(x, sy, ":")
            plt.show()
    else:
        sy = y

    decompargs = kwargs.pop('decompargs', None)
    if decompargs is None:
        peak_list = recognize_peaks(x, sy, num_components, correct=False)
    else:
        if debug:
            import molass.LowRank.ProportionalDecomposer
            reload(molass.LowRank.ProportionalDecomposer)
        from molass.LowRank.ProportionalDecomposer import decompose_icurve_proportionally
        peak_list = decompose_icurve_proportionally(x, sy, decompargs, **kwargs)

    ret_curves = []
    m = len(peak_list)
    if m > 0:
        assert elution_model == 'egh'   # currently
        if decompargs is None:
            areas = compute_areas(x, peak_list)
            init_area_ratios = areas/np.sum(areas)

            n = len(peak_list[0])
            shape = (m,n)
            max_y = icurve.get_max_xy()[1]
            tau_ratio = kwargs.get('tau_ratio', 0.5)
            area_weight = kwargs.get('area_weight', 0.1)

            def fit_objective(p):
                cy_list = []
                areas = []
                tau_penalty = 0
                for h, tr, sigma, tau in p.reshape(shape):
                    cy = egh(x, h, tr, sigma, tau)
                    tau_penalty += TAU_PENALTY_SCALE*max(0, abs(tau) - sigma*tau_ratio)
                    cy_list.append(cy)
                    areas.append(np.sum(cy))
                ty = np.sum(cy_list, axis=0)
                arear_ratios = np.array(areas)/np.sum(areas)
                return (np.sum((ty - sy)**2)
                        + max_y * area_weight * np.sum((arear_ratios - init_area_ratios)**2)
                        + tau_penalty)
            
            res = minimize(fit_objective, np.concatenate(peak_list), method='Nelder-Mead')
            opt_params = res.x.reshape(shape)
        else:
            opt_params = peak_list

        for params in opt_params:
            ret_curves.append(ComponentCurve(x, params))

    return ret_curves