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
    """ Guess initial parameters for the EDM model based on the given curve (x, y).
    N, T, N0, t0, poresize

    Parameters
    ----------
    x : array-like
        The x values of the curve.
    y : array-like
        The y values of the curve.
    init_params : tuple, optional
        Initial guess for the parameters. If None, a guess will be made.
    debug : bool, optional
        If True, debug information will be printed and plots will be shown.
    debug_info : dict, optional
        Additional debug information.

    Returns
    -------
    params : tuple
        Estimated parameters (N, T, me, mp, x0, tI, N0, poresize, timescale).
    """

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
    """ Guess initial parameters for multiple EDM component curves based on the given curve (x, y).
    N, T, N0, t0, poresize

    Parameters
    ----------
    x : array-like
        The x values of the curve.
    y : array-like
        The y values of the curve.
    xr_ccurves : list of EdmComponentCurve
        The list of EDM component curves.
    respect_egh : bool, optional
        If True, respect the EGH parameters of the component curves.
    debug : bool, optional
        If True, debug information will be printed and plots will be shown.

    Returns
    -------
    params_array : ndarray
        Estimated parameters for each component curve.
    """
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


def estimate_cedm_shared_params(x, y, xr_ccurves, debug=False, **kwargs):
    """Canonical estimator for CEDM (G2020) initial parameters.

    Combines rough per-component EDM fitting (:func:`guess_multiple_impl`)
    with a joint shared-column L-BFGS-B optimisation to produce physically
    meaningful CEDM params with varied ``b`` values and shared column
    parameters.

    Parameters
    ----------
    x : array-like
        Elution frame positions.
    y : array-like
        XR integrated intensity values.
    xr_ccurves : list
        Component curves.  Each must expose:

        - ``.x``     — array of frame positions (for peak-frame detection)
        - ``.y``     — array of intensity values (for peak-frame detection)
        - ``get_y()`` — method returning the component intensity (for rough fit)

    debug : bool, optional
        If ``True``, print optimisation diagnostics.
    **kwargs
        Forwarded to :func:`molass.SEC.Models.EdmOptimizer.optimize_edm_xr_decomposition`
        (e.g. ``e_bounds``, ``cinj_min``, ``suppress_positive_b_warning``).

    Returns
    -------
    cedm_colparams : np.ndarray, shape (4,)
        Shared column parameters ``[t0_sh, u_sh, e_sh, Dz_sh]``.
    abc_params : np.ndarray, shape (nc, 3)
        Per-component parameters ``[[a_0, b_0, cinj_0], ...]``.
    """
    if debug:
        from importlib import reload
        import molass.SEC.Models.EdmOptimizer
        reload(molass.SEC.Models.EdmOptimizer)
    from molass.SEC.Models.EdmOptimizer import optimize_edm_xr_decomposition

    nc = len(xr_ccurves)

    # Step 1: rough per-component estimate — provides Dz and cinj seed values
    rough_params = guess_multiple_impl(x, y, xr_ccurves, debug=debug)  # (nc, 7)

    # Step 2: build a minimal mock decomposition for optimize_edm_xr_decomposition
    class _MockIcurve:
        def get_xy(inner_self):
            return x, y

    class _MockDecomp:
        def __init__(inner_self):
            inner_self.num_components = nc
            inner_self.xr_icurve = _MockIcurve()
            inner_self.xr_ccurves = xr_ccurves  # need .x and .y for peak anchors

    # Step 3: shared-column optimisation
    # The optimizer resets b_init=0 and e_init=0.5 analytically, so the
    # b≈-4 from guess_multiple_impl does not pollute the result.
    kwargs.setdefault('shared_column', True)
    new_ccurves = optimize_edm_xr_decomposition(
        _MockDecomp(), rough_params, debug=debug, **kwargs
    )

    # Step 4: extract CEDM params — all curves share t0, u, e, Dz
    # params layout: [t0, u, a, b, e, Dz, cinj]
    p0 = new_ccurves[0].params
    cedm_colparams = np.array([p0[0], p0[1], p0[4], p0[5]])   # [t0_sh, u_sh, e_sh, Dz_sh]
    abc_params = np.array(
        [[cc.params[2], cc.params[3], cc.params[6]] for cc in new_ccurves]
    )  # (nc, 3): [a_k, b_k, cinj_k]

    return cedm_colparams, abc_params