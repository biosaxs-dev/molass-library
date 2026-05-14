"""
SEC.Models.EdmOptimizer.py
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from molass_legacy.Models.RateTheory.EDM import edm_impl

def optimize_edm_xr_decomposition(decomposition, init_params, **kwargs):
    """ Optimize the EDM decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    init_params : array-like
        The initial parameters for the EDM components.
    kwargs : dict
        Additional parameters for the optimization process.

        position_anchor_scale : float, optional
            Scale factor for the soft position constraint that keeps each
            EDM component centroid near its EGH peak frame.  Default 1e-5.
            Increase to enforce tighter position anchoring.

        e_bounds : tuple or None, optional
            Lower and upper bounds for the porosity parameter ``e`` (index 4
            of each component's 7-parameter vector).  Default ``(0.0, 1.0)``.
            Pass ``None`` to disable bounds on ``e`` (not recommended).

        shared_e : bool, optional
            If True, treat ``e`` as a single shared column parameter across
            all components instead of fitting it independently per component.
            This enforces the physical constraint that the interstitial
            porosity e = Vm/(Vm+Vs) is a column property, not a
            molecule-size-dependent property.  K_SEC (= ``a``) then carries
            all molecule-size information.  Default False.

    Returns
    -------
    new_xr_ccurves : list of EdmComponentCurve
        The optimized EDM component curves.
    """

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

    # EGH peak frames: used as soft position anchors so that the free
    # EDM optimization cannot collapse one component into the other.
    egh_peak_frames = np.array(
        [c.x[c.y.argmax()] for c in decomposition.xr_ccurves], dtype=float
    )
    position_anchor_scale = kwargs.get('position_anchor_scale', 1e-5)

    shape = init_params.shape

    def objective(p, return_cy_list=False):
        cy_list = []
        for params in p.reshape(shape):
            cy = edm_impl(x, *params)
            cy_list.append(cy)
        if return_cy_list:
            return cy_list
        ty = np.sum(cy_list, axis=0)
        data_error = np.sum((ty - y) ** 2)
        # Soft position constraint: penalise deviation of each component's
        # centroid from the corresponding EGH peak frame.  Using the centroid
        # (amplitude-independent distribution mean) prevents collapse even
        # when one component's amplitude approaches zero.
        position_penalty = 0.0
        for cy, egh_peak in zip(cy_list, egh_peak_frames):
            cy_abs_sum = np.sum(np.abs(cy))
            if cy_abs_sum > 0:
                centroid = np.sum(cy * x) / cy_abs_sum
                position_penalty += (centroid - egh_peak) ** 2
        return data_error + position_penalty * position_anchor_scale

    # E_IDX: index of the porosity parameter 'e' in the 7-param vector
    # [t0, u, a, b, e, Dz, cinj]
    E_IDX = 4
    e_bounds = kwargs.get('e_bounds', (0.0, 1.0))
    e_bounds_val = e_bounds if e_bounds is not None else (None, None)

    shared_e = kwargs.get('shared_e', False)

    if shared_e:
        # Reparameterise: p_flat = [e_shared, t0_0, u_0, a_0, b_0, Dz_0, cinj_0, t0_1, ...]
        # e is a single shared variable; each component has 6 free params (all except e).
        n_per_comp = shape[1] - 1  # 6 params: t0, u, a, b, Dz, cinj
        e_init = float(np.clip(init_params[:, E_IDX].mean(), 0.01, 0.99))
        other_init = np.delete(init_params, E_IDX, axis=1)  # (N_comp, 6)
        p0_shared = np.concatenate([[e_init], other_init.flatten()])

        def objective_shared(p_flat, return_cy_list=False):
            e_val = p_flat[0]
            other = p_flat[1:].reshape(shape[0], n_per_comp)
            cy_list = []
            for other_params in other:
                full_params = np.insert(other_params, E_IDX, e_val)
                cy_list.append(edm_impl(x, *full_params))
            if return_cy_list:
                return cy_list
            ty = np.sum(cy_list, axis=0)
            data_error = np.sum((ty - y) ** 2)
            position_penalty = 0.0
            for cy, egh_peak in zip(cy_list, egh_peak_frames):
                cy_abs_sum = np.sum(np.abs(cy))
                if cy_abs_sum > 0:
                    centroid = np.sum(cy * x) / cy_abs_sum
                    position_penalty += (centroid - egh_peak) ** 2
            return data_error + position_penalty * position_anchor_scale

        bounds_shared = [e_bounds_val] + [(None, None)] * (shape[0] * n_per_comp)
        result_shared = minimize(objective_shared, p0_shared, bounds=bounds_shared, method='L-BFGS-B')
        e_fitted = result_shared.x[0]
        other_fitted = result_shared.x[1:].reshape(shape[0], n_per_comp)

        if debug:
            print(f"  shared e = {e_fitted:.4f}")

        new_xr_ccurves = []
        for other_params in other_fitted:
            full_params = np.insert(other_params, E_IDX, e_fitted)
            new_xr_ccurves.append(EdmComponentCurve(x, full_params))
        return new_xr_ccurves

    # --- Independent-e mode (original behaviour) ---
    # Build per-parameter bounds: only e (index 4) is physically bounded to [0, 1].
    # All other parameters (t0, u, a, b, Dz, cinj) are left unbounded.
    n_params_per_comp = shape[1]
    if e_bounds is not None:
        bounds = []
        for _ in range(shape[0]):
            for j in range(n_params_per_comp):
                bounds.append(e_bounds if j == E_IDX else (None, None))
    else:
        bounds = None

    result = minimize(objective, init_params.flatten(), bounds=bounds, method='L-BFGS-B')
    if debug:
        debug_plot_params(x, y, result.x.reshape(shape), "optimize: after minimize")
        cy_list_opt = objective(result.x, return_cy_list=True)
        for i, (cy, egh_peak) in enumerate(zip(cy_list_opt, egh_peak_frames)):
            cy_abs_sum = np.sum(np.abs(cy))
            centroid = np.sum(cy * x) / cy_abs_sum if cy_abs_sum > 0 else float('nan')
            print(f"  Component {i}: centroid={centroid:.1f}  EGH peak={egh_peak:.1f}  diff={centroid - egh_peak:.1f}")

    new_xr_ccurves = []
    for params in result.x.reshape(shape):
        ccurve = EdmComponentCurve(x, params)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves
