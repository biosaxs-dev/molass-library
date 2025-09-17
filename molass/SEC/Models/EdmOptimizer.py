"""
SEC.Models.EdmOptimizer.py
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from molass_legacy.Models.RateTheory.EDM import edm_impl
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf, DEFUALT_TIMESCALE

def optimize_edm_xr_decomposition(decomposition, init_params, **kwargs):
    # N, T, N0, t0, poresize
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.EdmComponentCurve
        reload(molass.SEC.Models.EdmComponentCurve)
    from .EdmComponentCurve import EdmColumn, EdmComponentCurve
    num_components = decomposition.num_components
    x, y = decomposition.xr_icurve.get_xy()

    if debug:
        def debug_plot_params(x, y, params_array, title):
            print("params=", params_array)
            fig, ax = plt.subplots()
            ax.set_title(title, fontsize=16)
            ax.plot(x, y)
            for params in params_array:
                ax.plot(x, edm_impl(x, *params))
            fig.tight_layout()
            plt.show()
        debug_plot_params(x, y, init_params, "optimize: before minimize")

    shape = init_params.shape

    def objective(p):
        cy_list = []
        for params in p.reshape(shape):
            cy = edm_impl(x, *params)
            cy_list.append(cy)
        y_ = np.sum(cy_list, axis=0)
        return np.sum((y_ - y)**2)

    result = minimize(objective, init_params.flatten())
    if debug:
        debug_plot_params(x, y, result.x.reshape(shape), "optimize: after minimize")

    new_xr_ccurves = []
    for params in result.x.reshape(shape):
        ccurve = EdmComponentCurve(x, params)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves
