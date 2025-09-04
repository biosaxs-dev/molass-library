"""
SEC.Models.EdmEstimatorImpl.py
"""
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from molass_legacy.KekLib.BasicUtils import Struct
from molass_legacy.Models.ElutionModelUtils import compute_4moments
from molass_legacy.Models.RateTheory.EDM import MIN_CINJ, MAX_CINJ, edm_impl
from molass.SEC.Models.Simple import egh

save_reg_data_fh = None

def guess(x, y, init_params=None, debug=False, debug_info=None):
    if debug:
        from importlib import reload
        import molass_legacy.Models.RateTheory.RobustEDM
        reload(molass_legacy.Models.RateTheory.RobustEDM)
    from molass_legacy.Models.RateTheory.RobustEDM import guess_init_params

    if debug:
        def debug_plot_params(x, y, params, title):
            print("params=", params)
            fig, ax = plt.subplots()
            ax.set_title("guess debug", fontsize=16)
            ax.plot(x, y)
            ax.plot(x, edm_impl(x, *params))
            fig.tight_layout()
            plt.show()

    if init_params is None:
        M = compute_4moments(x, y)
        # init_params = guess_init_params_better(x, y, M)
        init_params = guess_init_params(M)
        area = np.sum(y)
        y_i = edm_impl(x, *init_params)
        area_i = np.sum(y_i)
        ratio = area_i/area
        print("area ratio=", ratio)

    def objective(p):
        y_ = edm_impl(x, *p)
        return np.sum((y_ - y)**2)

    ret = minimize(objective, init_params)

    if debug:
        print("M=", M)
        debug_plot_params(x, y, ret.x, "guess: after minimize")

    return ret.x

def guess_multiple_impl(x, y, xr_ccurves, respect_egh=False, debug=False):
    num_components = len(xr_ccurves)

    cy_list = []
    edm_params_list  = []
    for ccurve in xr_ccurves:
        cy = ccurve.get_y()
        params = guess(x, cy)
        edm_params_list.append(params)

    def cinj_ovjective(p, return_cy_list=False):
        cy_list = []
        for i, params in enumerate(edm_params_list):
            params_ = params.copy()
            params_[6] = p[i]
            cy = edm_impl(x, *params_)
            cy_list.append(cy)
        if return_cy_list:
            return cy_list
        ty = np.sum(cy_list, axis=0)
        return np.sum((y - ty)**2)

    init_cinjs = [p[6] for p in edm_params_list]
    bounds = [(MIN_CINJ, MAX_CINJ)] * num_components
    ret = minimize(cinj_ovjective, init_cinjs, method="Nelder-Mead", bounds=bounds)
    edm_cy_list = cinj_ovjective(ret.x, return_cy_list=True)

    peak_pos = []
    for i, params in enumerate(edm_params_list):
        params[6] = ret.x[i]
        m = np.argmax(edm_cy_list[i])
        peak_pos.append(x[m])
    sort_pairs = sorted(zip(peak_pos, edm_params_list), key=lambda x: x[0])
    final_params_list = [pair[1] for pair in sort_pairs]
    return np.array(final_params_list)