"""
    LowRank.CurveDecomposer.py

    This module contains the decompose functions used to decompose
    a given I-curve into a set of component curves.
"""
from importlib import reload
import numpy as np
from scipy.optimize import minimize
from molass_legacy.QuickAnalysis.ModeledPeaks import recognize_peaks
from molass.SEC.Models.Simple import egh

TAU_PENALTY_SCALE = 100
NPLATES_PENALTY_SCALE = 1e-4
MEAN_ORDER_PENALTY_SCALE = 1e5
SIGMA_ORDER_PENALTY_SCALE = 1e5
GUINIER_PENALTY_SCALE = 1e5
VERY_SMALL_VALUE = 1e-10

def safe_log10(x):
    """
    Compute the logarithm base 10 of x, returning a large negative number for non-positive x.

    Parameters
    ----------
    x : float
        The input value.

    Returns
    -------
    float
        The logarithm base 10 of x, or -10 if x is non-positive.
    """
    return np.log10(x) if x > VERY_SMALL_VALUE else -10

def compute_areas(x, peak_list):
    """Compute the areas under the peaks defined by peak_list over the x values.

    Parameters
    ----------
    x : array-like
        The x values.
    peak_list : list of tuples
        The list of peak parameters, where each tuple contains (height, tR, sigma, tau).

    Returns
    -------
    areas : array-like
        The areas under each peak.
    """
    areas = []
    for params in peak_list:
        y = egh(x, *params)
        areas.append(np.sum(y))
    return np.array(areas)

class CurveDecomposer:
    """ A class for decomposing curves into component curves.
    """
    def __init__(self):
        pass

def decompose_icurve_impl(icurve, num_components, **kwargs):
    """
    Decompose a curve into component curves.
    Parameters
    ----------
    icurve : Curve
        The input curve to be decomposed.
    num_components : int
        The number of components to decompose into.
    curve_model : str, optional
        The model to use for curve decomposition.
        Currently, only 'EGH' (Exponentially-Gaussian Hybrid) is supported. Default is 'EGH'.
    smoothing : bool, optional
        Whether to apply smoothing to the input curve before decomposition. Default is False.
    debug : bool, optional
        If True, print debug information and plot intermediate results. Default is False.
    kwargs : dict, optional
        Additional keyword arguments for decomposition.
        Possible keys include:
            - decompargs: dict or None
                If provided, use these arguments for decomposition instead of peak recognition.
            - tau_limit: float
                Limit for the tau parameter in the EGH model. Default is 0.5.
            - area_weight: float
                Weight for the area proportion penalty in the fitting objective. Default is 0.1.
            - proportions: list of float or None
                Target proportions for the areas of the components. If None, use areas from initial peak recognition.
            - sec_constraints: bool
                If True, apply SEC-related constraints during fitting. Default is False.
            - data_matrix: array-like or None
                The data matrix for SEC constraints. Required if sec_constraints is True.
            - qv: array-like or None
                The q-values corresponding to the data matrix. Required if sec_constraints is True.
            - num_plates: int or None
                The number of plates to use for decomposition. If None, use the default value.
            - randomize: float
                Standard deviation of Gaussian noise to add to initial parameters for randomization. Default is 0 (no randomization).
            - seed: int or None
                Random seed for parameter randomization. Default is None.
            - global_opt: bool
                If True, use global optimization (basinhopping) for fitting. Default is False.
    Returns
    -------
    ret_curves : list of ComponentCurve
        The list of decomposed component curves.
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
        peak_list = recognize_peaks(x, sy, num_peaks=num_components, exact_num_peaks=num_components, correct=False)
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

            sec_constraints = kwargs.get('sec_constraints', False)
            if sec_constraints:
                from bisect import bisect_right
                M = kwargs.get('data_matrix', None)
                qv = kwargs.get('qv', None)
                jqv = bisect_right(qv, 0.005)
                from molass.LowRank.LowRankInfo import get_denoised_data
                M_ = get_denoised_data(M, rank=num_components)
            else:
                M_ = None
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
                shaped_params = p.reshape(shape)
                if num_components > 1:
                    mean_order_penalty = min(0, np.min(np.diff(shaped_params[:, 1])))**2
                    sigma_order_penalty = min(0, np.min(np.diff(shaped_params[:, 2])))**2
                else:
                    mean_order_penalty = 0
                    sigma_order_penalty = 0
                for h, tr, sigma, tau in shaped_params:
                    cy = egh(x, h, tr, sigma, tau)
                    tau_penalty += max(0, abs(tau) - sigma*tau_limit)
                    cy_list.append(cy)
                    areas.append(np.sum(cy))
                    if num_plates is not None:
                        ndev_penalty = ((tr - tI)**2 / (sigma**2 + tau**2) - N**2)**2
                ty = np.sum(cy_list, axis=0)
                area_proportions = np.array(areas)/np.sum(areas)
                if M_ is None:
                    guinier_penalty = 0
                else:
                    try:
                        C = np.array(cy_list)
                        Cinv = np.linalg.pinv(C)
                        P = M_ @ Cinv
                        slope_proxy = P[0,:] - P[jqv,:]
                        positive_slope_penalty = min(0, np.min(slope_proxy))**2
                        size_order_penalty = max(0, np.max(np.diff(slope_proxy)))**2
                        guinier_penalty = positive_slope_penalty + size_order_penalty
                    except:
                        guinier_penalty = GUINIER_PENALTY_SCALE     # very high penalty

                return (safe_log10(np.sum((ty - sy)**2) + area_weight * max_y * np.sum((area_proportions - target_proportions)**2))
                        + safe_log10(TAU_PENALTY_SCALE * tau_penalty)
                        + safe_log10(NPLATES_PENALTY_SCALE * ndev_penalty)
                        + safe_log10(MEAN_ORDER_PENALTY_SCALE * mean_order_penalty)
                        + safe_log10(SIGMA_ORDER_PENALTY_SCALE * sigma_order_penalty)
                        + safe_log10(GUINIER_PENALTY_SCALE * guinier_penalty)
                        )

            moment = icurve.get_moment()
            mean, std = moment.get_meanstd()

            init_params = np.array(peak_list)
            min_height = np.max(init_params[:, 0])*0.05
            max_sigma = std*2
            min_sigma = std*0.1
            num_major_peaks = icurve.get_num_major_peaks()
            if num_major_peaks > 1:
                mean_allow = 5 * std
            else:
                mean_allow = 3 * std
            bounds = [(min_height, None), (mean-mean_allow, mean+mean_allow), (min_sigma, max_sigma), (-max_sigma, max_sigma)] * num_components
            init_params = init_params.flatten()
            randomize = kwargs.get('randomize', 0)
            if randomize > 0:
                seed = kwargs.get('seed', None)
                if seed is not None:
                    np.random.seed(seed)
                init_params += np.random.normal(0, randomize, size=init_params.shape)

            if debug:
                import molass.ScipyUtils.BoundsChecker
                from importlib import reload
                reload(molass.ScipyUtils.BoundsChecker)
            from molass.ScipyUtils.BoundsChecker import check_egh_bounds
            init_params = check_egh_bounds(x, y, init_params, bounds, modify=True, debug=debug)

            global_opt = kwargs.get('global_opt', False)
            if global_opt:
                from scipy.optimize import basinhopping
                minimizer_kwargs = dict(method="Nelder-Mead", bounds=bounds)
                res = basinhopping(fit_objective, init_params, minimizer_kwargs=minimizer_kwargs)
            else:
                res = minimize(fit_objective, init_params, method='Nelder-Mead', bounds=bounds)
            opt_params = res.x.reshape(shape)
        else:
            opt_params = peak_list

        for params in opt_params:
            ret_curves.append(ComponentCurve(x, params))

    return ret_curves