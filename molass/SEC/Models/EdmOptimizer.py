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

        shared_column : bool, optional
            If True, enforce the full constrained-EDM parameterisation where
            ``t0``, ``u``, ``e``, ``Dz`` are shared column parameters and
            only ``a`` (K_SEC), ``b``, and ``cinj`` are per-component.

            This is the recommended mode for K_SEC identification.  With
            over-parameterised (free) EDM, the optimiser can absorb peak
            position into ``t0``/``u`` and leave ``a`` near zero for all
            components, making Spearman(Rg, a) meaningless.  With constrained
            EDM, peak positions are explained solely by ``a``-differences,
            yielding Spearman(Rg, a) = -1.000 for well-separated SEC data.

            Parameter vector layout::

                [t0_sh, u_sh, e_sh, Dz_sh,
                 a_0, b_0, cinj_0,
                 a_1, b_1, cinj_1, ...]

            Default bounds applied when ``shared_column=True``:
            - ``e_bounds`` → ``(0.2, 0.85)`` (physical SEC total-porosity range)
            - ``cinj_min`` → ``0.05`` (prevents component collapse to zero)

            These defaults can be overridden via:
            - ``e_bounds`` kwarg (same meaning as the top-level kwarg)
            - ``cinj_min`` kwarg

            Default True.  Pass ``False`` to use unconstrained (free) EDM,
            which is deprecated and will be removed in a future release.

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

    _unset = object()
    shared_column = kwargs.get('shared_column', _unset)
    if shared_column is _unset:
        shared_column = True  # CEDM is the default; free-EDM is deprecated
    elif not shared_column:
        import warnings
        warnings.warn(
            "shared_column=False (free-EDM) is deprecated and will be removed in a future release. "
            "Use the default shared_column=True (constrained-EDM / CEDM) instead.",
            DeprecationWarning,
            stacklevel=3,
        )

    if shared_column:
        # --- Constrained-EDM mode ---
        # Parameter vector: [t0_sh, u_sh, e_sh, Dz_sh,  a_0,b_0,cinj_0, a_1,b_1,cinj_1, ...]
        # Shared indices in the 7-param vector: T0=0, U=1, E=4, DZ=5
        # Per-component indices: A=2, B=3, CINJ=6
        L_EDM = 30.0  # column length hardcoded in edm_func / edm_impl
        N_SHARED = 4  # t0, u, e, Dz
        N_PER_COMP = 3  # a, b, cinj
        n_comp = shape[0]

        # Shared-column bounds; prefer caller-supplied e_bounds over the tight default.
        sc_e_bounds = kwargs.get('e_bounds', (0.2, 0.85))
        cinj_min = kwargs.get('cinj_min', 0.05)

        # --- analytical init for shared params ---
        t0_sh = float(init_params[:, 0].min())
        # u_sh: choose so that the void time is ~10% shorter than the fastest peak delay
        peak_delay = float(egh_peak_frames.min()) - t0_sh
        if peak_delay <= 0:
            peak_delay = 1.0  # guard
        void_time = peak_delay / 1.1  # leave 10% head-room so all a_init > 0
        u_sh = L_EDM / void_time
        Dz_sh = float(init_params[:, 5].mean())  # DZ_IDX = 5

        # b=0 is the linear-limit start; per-component free-EDM b values are
        # unreliable (can produce b≪0, causing gam3 overflow).
        cinj_init = np.maximum(init_params[:, 6], cinj_min)  # CINJ_IDX = 6

        # Analytical a_init at e=0.5 (F=1.0 — typical SEC total porosity).
        # Per-component free-EDM e tends to over-estimate (~0.85, F≈0.17),
        # forcing a≫1.  Starting at e=0.5 keeps a in the physical K_SEC range.
        e_sh_init = 0.5
        F_sh_init = (1.0 - e_sh_init) / e_sh_init  # = 1.0
        a_init = ((egh_peak_frames - t0_sh) / void_time - 1.0) / max(F_sh_init, 1e-3)
        a_init = np.maximum(a_init, 0.01)

        # Bounds
        # t0: left unconstrained — the optimizer starts from the analytical
        #     value (t0_sh ≈ free-EDM minimum) and L-BFGS-B follows the gradient.
        # b:  left unconstrained — extreme b values give the EDM curve the
        #     flexibility to match asymmetric elution peaks.  nan_to_num in the
        #     objective handles any numerical overflow that arises.
        sc_bounds = [
            (None, None),             # t0_sh: unconstrained (starts at analytical value)
            (1e-3, None),             # u_sh  — must be positive
            sc_e_bounds,              # e_sh
            (1e-6, None),             # Dz_sh — must be positive
        ]
        pc_bounds = []
        for _ in range(n_comp):
            pc_bounds += [
                (0.0, None),          # a_i   (K_SEC ≥ 0)
                (None, None),         # b_i   (unconstrained; nan_to_num guards overflow)
                (cinj_min, None),     # cinj_i (prevents collapse)
            ]
        sc_bounds = sc_bounds + pc_bounds

        def objective_sc(p_flat, return_cy_list=False):
            t0_v, u_v, e_v, Dz_v = p_flat[:N_SHARED]
            per_comp = p_flat[N_SHARED:].reshape(n_comp, N_PER_COMP)
            cy_list = []
            for a_v, b_v, cinj_v in per_comp:
                full = np.array([t0_v, u_v, a_v, b_v, e_v, Dz_v, cinj_v])
                # Replace NaN/Inf (from overflow in pathological regions) with 0
                # so the position penalty is still applied to out-of-range curves.
                cy = np.nan_to_num(edm_impl(x, *full), nan=0.0, posinf=0.0, neginf=0.0)
                cy_list.append(cy)
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
                else:
                    # Curve is zero everywhere — apply a strong penalty so the
                    # optimizer does not "hide" a component outside the data range.
                    position_penalty += (x[-1] - egh_peak) ** 2
            return data_error + position_penalty * position_anchor_scale

        # Single optimization from the analytical starting point.
        # No two-phase, no multi-start — L-BFGS-B from (e=0.5, b=0) follows
        # the gradient into the physically meaningful basin.  Unconstrained t0
        # and b allow the EDM curves to take flexible shapes that better fit the
        # data while still preserving the a-value ordering (K_SEC identifiability).
        per_comp_init = np.column_stack([a_init, np.zeros(n_comp), cinj_init]).flatten()
        p0_sc = np.concatenate([np.array([t0_sh, u_sh, e_sh_init, Dz_sh]), per_comp_init])

        result_sc = minimize(objective_sc, p0_sc, bounds=sc_bounds, method='L-BFGS-B',
                             options={'maxiter': 20000, 'ftol': 1e-14, 'gtol': 1e-9})

        t0_fit, u_fit, e_fit, Dz_fit = result_sc.x[:N_SHARED]
        per_comp_fit = result_sc.x[N_SHARED:].reshape(n_comp, N_PER_COMP)

        if debug:
            print(f"  fval={result_sc.fun:.6g}  success={result_sc.success}")
            print(f"  shared column: t0={t0_fit:.2f}  u={u_fit:.4f}  e={e_fit:.4f}  Dz={Dz_fit:.4f}")
            for i, (a_v, b_v, cinj_v) in enumerate(per_comp_fit):
                print(f"  comp {i}: a={a_v:.4f}  b={b_v:.4f}  cinj={cinj_v:.4f}")

        new_xr_ccurves = []
        for a_v, b_v, cinj_v in per_comp_fit:
            full_params = np.array([t0_fit, u_fit, a_v, b_v, e_fit, Dz_fit, cinj_v])
            new_xr_ccurves.append(EdmComponentCurve(x, full_params, model='cedm'))
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
