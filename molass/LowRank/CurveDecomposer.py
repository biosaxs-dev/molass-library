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

TAU_PENALTY_SCALE = 100
NPLATES_PENALTY_SCALE = 1e-4
VERY_SMALL_VALUE = 1e-10


def safe_log10(x):
    """
    Compute the logarithm base 10 of x, returning a large negative number for non-positive x.
    """
    return np.log10(x) if x > VERY_SMALL_VALUE else -10

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

    curve_model = kwargs.get('curve_model', 'EGH')
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
        assert curve_model == 'EGH'   # currently
        if decompargs is None:
 
            n = len(peak_list[0])
            shape = (m,n)
            max_y = icurve.get_max_xy()[1]
            tau_limit = kwargs.get('tau_limit', 0.5)
            area_weight = kwargs.get('area_weight', 0.1)
            proportions = kwargs.get('proportions', None)
            if proportions is None:
                areas = compute_areas(x, peak_list)
                target_proportions = areas/np.sum(areas)
            else:
                target_proportions = np.array(proportions)

            num_plates = kwargs.get('num_plates', None)
            if num_plates is not None:
                N = np.sqrt(num_plates)
                params_array = np.array(peak_list)
                main_peak = np.argmax(params_array[:, 0])  # find the main peak
                main_params = peak_list[main_peak]
                main_tR, main_sigma, main_tau = main_params[1:4]
                tR = np.sqrt(main_sigma**2 + main_tau**2) * N
                # tR = t - tI
                tI = main_tR - tR
                if debug:
                    import matplotlib.pyplot as plt
                    print(f"N={N}, main_peak={main_peak}, main_params={main_params}")
                    fig, ax = plt.subplots()
                    ax.set_title("decompose_icurve_impl debug")
                    ax.plot(x, sy, label='sy')
                    for i, params in enumerate(peak_list):
                        cy = egh(x, *params)
                        ax.plot(x, cy, ":", label=f'component {i+1}')
                    ax.axvline(tI, color='red', linestyle='--', label='tI')        
                    ax.legend()
                    plt.show()

            def fit_objective(p):
                cy_list = []
                areas = []
                tau_penalty = 0
                ndev_penalty = 0
                for h, tr, sigma, tau in p.reshape(shape):
                    cy = egh(x, h, tr, sigma, tau)
                    tau_penalty += max(0, abs(tau) - sigma*tau_limit)
                    cy_list.append(cy)
                    areas.append(np.sum(cy))
                    if num_plates is not None:
                        ndev_penalty = ((tr - tI)**2 / (sigma**2 + tau**2) - N**2)**2
                ty = np.sum(cy_list, axis=0)
                area_proportions = np.array(areas)/np.sum(areas)

                return (safe_log10(np.sum((ty - sy)**2) + area_weight * max_y * np.sum((area_proportions - target_proportions)**2))
                        + safe_log10(TAU_PENALTY_SCALE * tau_penalty)
                        + safe_log10(NPLATES_PENALTY_SCALE * ndev_penalty)
                        )

            init_params = np.concatenate(peak_list)
            randomize = kwargs.get('randomize', 0)
            if randomize > 0:
                seed = kwargs.get('seed', None)
                if seed is not None:
                    np.random.seed(seed)
                init_params += np.random.normal(0, randomize, size=init_params.shape)

            global_opt = kwargs.get('global_opt', False)
            if global_opt:
                from scipy.optimize import basinhopping
                minimizer_kwargs = dict(method="Nelder-Mead")
                res = basinhopping(fit_objective, init_params, minimizer_kwargs=minimizer_kwargs)
            else:
                res = minimize(fit_objective, init_params, method='Nelder-Mead')
            opt_params = res.x.reshape(shape)
        else:
            opt_params = peak_list

        for params in opt_params:
            ret_curves.append(ComponentCurve(x, params))

    return ret_curves