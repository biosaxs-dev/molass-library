"""
SEC.Models.EdmOptimizer.py
"""
import warnings
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from molass_legacy.Models.RateTheory.EDM import edm_impl

_POSITIVE_B_WARNING = (
    "EDM fitted b = {b_vals} > 0 for component(s) {comps}.  "
    "In SEC, tailing is normally caused by finite mass-transfer kinetics (b = 0), "
    "not by Langmuir adsorption (b > 0).  A positive b may indicate secondary "
    "adsorption, column overloading, or the model compensating for kinetic tailing "
    "with the wrong mechanism.  "
    "Pass suppress_positive_b_warning=True to silence this warning."
)

_B_WARN_THRESHOLD = 1e-3   # b values below this are treated as numerical zero

def _check_positive_b(b_values, suppress, stacklevel=4):
    """Issue a UserWarning if any fitted b > _B_WARN_THRESHOLD (unless suppressed)."""
    if suppress:
        return
    pos = [(i, float(b)) for i, b in enumerate(b_values) if b > _B_WARN_THRESHOLD]
    if pos:
        comps = [i for i, _ in pos]
        vals  = [f"{v:.4f}" for _, v in pos]
        warnings.warn(
            _POSITIVE_B_WARNING.format(b_vals=", ".join(vals), comps=comps),
            UserWarning,
            stacklevel=stacklevel,
        )

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

        suppress_positive_b_warning : bool, optional
            If True, suppress the UserWarning that is issued when any fitted
            ``b`` parameter is positive.  In SEC, b > 0 (Langmuir adsorption)
            is physically unusual — right-tailing is normally kinetic (b = 0).
            A positive b may indicate secondary adsorption, overloading, or
            the model compensating for kinetic tailing with the wrong mechanism.
            Default False.

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

        # b is at index 3 in the 6-element other_params ([t0,u,a,b,Dz,cinj])
        b_fitted_shared_e = other_fitted[:, 3]
        _check_positive_b(b_fitted_shared_e,
                          suppress=kwargs.get('suppress_positive_b_warning', False))
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
        # b:  can be constrained via kwargs (e.g., b_bounds=(-2, 0.5) from
        #     auto-derived EGH tau analysis).  Default: unconstrained.
        # a:  can be constrained via kwargs (e.g., a_bounds=(0, 2.5) from
        #     auto-derived EGH retention analysis).  Default: (0, ∞).
        
        # Extract bounds from kwargs (auto-derived in EdmEstimator if not specified)
        a_bounds_kw = kwargs.get('a_bounds', None)
        b_bounds_kw = kwargs.get('b_bounds', None)
        
        sc_bounds = [
            (None, None),             # t0_sh: unconstrained (starts at analytical value)
            (1e-3, None),             # u_sh  — must be positive
            sc_e_bounds,              # e_sh
            (1e-6, None),             # Dz_sh — must be positive
        ]
        pc_bounds = []
        for _ in range(n_comp):
            # Per-component bounds: apply kwargs overrides if present
            a_bound = a_bounds_kw if a_bounds_kw is not None else (0.0, None)
            b_bound = b_bounds_kw if b_bounds_kw is not None else (None, None)
            pc_bounds += [
                a_bound,              # a_i   (K_SEC, user or auto-derived bounds)
                b_bound,              # b_i   (user or auto-derived bounds)
                (cinj_min, None),     # cinj_i (prevents collapse)
            ]
        sc_bounds = sc_bounds + pc_bounds
        
        # Order penalty scale: enforce K_SEC monotonicity (a[0] ≤ a[1] ≤ ...)
        # In SEC, earlier-eluting components have larger Rg → more excluded → smaller a.
        # kwargs can override via 'a_order_penalty_scale' (default 1e-3).
        a_order_penalty_scale = kwargs.get('a_order_penalty_scale', 1e-3)

        def objective_sc(p_flat, return_cy_list=False):
            t0_v, u_v, e_v, Dz_v = p_flat[:N_SHARED]
            per_comp = p_flat[N_SHARED:].reshape(n_comp, N_PER_COMP)
            cy_list = []
            a_values = []
            for a_v, b_v, cinj_v in per_comp:
                a_values.append(a_v)
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
            
            # Order penalty: penalize when a[i] > a[i+1] (wrong order)
            # Components are ordered by EGH peak position (early → late elution).
            # SEC principle: early elution → larger Rg → smaller K_SEC (a).
            # So a[0] ≤ a[1] ≤ ... ≤ a[n-1] is the expected ordering.
            order_penalty = 0.0
            for i in range(n_comp - 1):
                if a_values[i] > a_values[i+1]:
                    # Wrong order: penalize the squared violation
                    order_penalty += (a_values[i] - a_values[i+1]) ** 2
            
            return (data_error + 
                    position_penalty * position_anchor_scale +
                    order_penalty * a_order_penalty_scale)

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

        _check_positive_b(per_comp_fit[:, 1],
                          suppress=kwargs.get('suppress_positive_b_warning', False))
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

    # b is at index 3 in the 7-element free-EDM param vector [t0,u,a,b,e,Dz,cinj]
    b_fitted_free = result.x.reshape(shape)[:, 3]
    _check_positive_b(b_fitted_free,
                      suppress=kwargs.get('suppress_positive_b_warning', False))
    new_xr_ccurves = []
    for params in result.x.reshape(shape):
        ccurve = EdmComponentCurve(x, params)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves


def refine_edm_per_component(edm_ccurves, x, y, **kwargs):
    """Lighter second XR pass: fix shared column, refine per-component (a, b, cinj).

    This is the EDM analog of SDM's UV pass (which fixes XR and only refines
    mapping + UV scales).  The shared column parameters ``(t0, u, e, Dz)`` are
    extracted from the already-optimised ``edm_ccurves`` and held fixed.  Only
    the per-component ``(a, b, cinj)`` parameters are free.

    This split is physically motivated:
    - Shared column (t0, u, e, Dz): column geometry, determined by the first full
      pass and not expected to improve from further unconstrained refinement.
    - Per-component (a = K_SEC, b, cinj): molecule-specific, benefit from
      refinement once the column baseline is stable.

    Parameters
    ----------
    edm_ccurves : list of EdmComponentCurve
        Output of a previous :func:`optimize_edm_xr_decomposition` call.
        All curves must share the same ``(t0, u, e, Dz)`` (i.e. the result of a
        ``shared_column=True`` run).
    x : array-like
        Elution frame positions (same as used in the first pass).
    y : array-like
        XR integrated intensity (same as used in the first pass).
    kwargs : dict
        cinj_min : float, optional
            Lower bound for cinj.  Default 0.05.
        b_max : float, optional
            Global override for the b upper bound.  When omitted (default),
            the automatic strategy is used:

            - ``n_comp < 4``: per-component ceiling at the Pass-1 b value.
              b can decrease (toward physical values) but not increase.
              Legitimate b > 0 from 2/3-component Pass-1 results is preserved.
            - ``n_comp >= 4``: ``min(b_pass1_i, 0.0)`` per component.
              High-component-count systems tend to drift to large positive b
              (EDM overflow territory); forcing b ≤ 0 resets the optimizer
              into the physically correct linear-SEC basin.

            Pass an explicit float to override for all components (e.g. 0.0
            to force the physical regime regardless of component count).
        position_anchor_scale : float, optional
            Scale for soft centroid-to-EGH-peak penalty.  Default 1e-5.
        suppress_positive_b_warning : bool, optional
            Suppress the b > 0 UserWarning.  Default False.
        debug : bool, optional

    Returns
    -------
    refined_ccurves : list of EdmComponentCurve
    """
    from .EdmComponentCurve import EdmComponentCurve

    debug = kwargs.get('debug', False)
    cinj_min = kwargs.get('cinj_min', 0.05)
    position_anchor_scale = kwargs.get('position_anchor_scale', 1e-5)

    # Extract shared column from first component (all share them by construction).
    p0 = edm_ccurves[0].params   # [t0, u, a, b, e, Dz, cinj]
    t0_fixed, u_fixed, e_fixed, Dz_fixed = p0[0], p0[1], p0[4], p0[5]

    n_comp = len(edm_ccurves)
    # b bounds strategy:
    # For n_comp < 4 (2/3-component): anchor to Pass-1 value per component.
    #   b cannot increase beyond what Pass-1 found, but can decrease.
    #   Pass-1 b > 0 may be physically legitimate for 2/3-comp systems.
    # For n_comp >= 4: additionally enforce b ≤ 0.
    #   High-component-count systems tend to drift to large positive b values
    #   that cause EDM overflow.  Forcing b ≤ 0 (linear SEC regime) resets
    #   the optimizer into a stable, physically correct basin.
    #   NOTE: use hard 0.0 (NOT min(b_pass1, 0)) — if b_pass1 < 0 for some
    #   components, min(b_pass1, 0) = b_pass1 < 0, which over-constrains those
    #   components and prevents the optimizer from reaching the good basin.
    #   (Tested: SAMPLE4 SV improves from -83 → +79 with b ≤ 0 exactly.)
    _b_max_global = kwargs.get('b_max', None)  # None = use automatic strategy
    _b_zero_cap = (n_comp >= 4)  # enforce b ≤ 0 for 4+ component systems

    # EGH peak frames: soft position anchors to prevent component collapse.
    egh_peak_frames = np.array(
        [c.x[c.y.argmax()] for c in edm_ccurves], dtype=float
    )

    # Initial per-component params from previous pass.
    abc_init = np.array([[cc.params[2], cc.params[3], cc.params[6]]
                         for cc in edm_ccurves])   # (n_comp, 3): a, b, cinj

    N_PER_COMP = 3  # a, b, cinj

    def objective_abc(p_flat, return_cy_list=False):
        per_comp = p_flat.reshape(n_comp, N_PER_COMP)
        cy_list = []
        for a_v, b_v, cinj_v in per_comp:
            full = np.array([t0_fixed, u_fixed, a_v, b_v, e_fixed, Dz_fixed, cinj_v])
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
                position_penalty += (x[-1] - egh_peak) ** 2
        return data_error + position_penalty * position_anchor_scale

    abc_bounds = []
    for cc in edm_ccurves:
        b_pass1 = float(cc.params[3])
        if _b_max_global is not None:
            b_upper = _b_max_global
        elif _b_zero_cap:
            b_upper = 0.0                 # hard b ≤ 0 for 4+ comp: prevents EDM overflow
        else:
            b_upper = b_pass1             # b ≤ b_pass1 for 2/3 comp: preserves physical b
        abc_bounds += [
            (0.0, None),          # a (K_SEC ≥ 0)
            (None, b_upper),      # b (adaptive upper bound — see strategy comment above)
            (cinj_min, None),     # cinj
        ]

    result = minimize(
        objective_abc, abc_init.flatten(),
        bounds=abc_bounds, method='L-BFGS-B',
        options={'maxiter': 10000, 'ftol': 1e-14, 'gtol': 1e-9}
    )

    if debug:
        print(f"  refine_edm_per_component: fval={result.fun:.6g}  success={result.success}")
        per_comp_fit = result.x.reshape(n_comp, N_PER_COMP)
        for i, (a_v, b_v, cinj_v) in enumerate(per_comp_fit):
            print(f"  comp {i}: a={a_v:.4f}  b={b_v:.4f}  cinj={cinj_v:.4f}")

    _check_positive_b(
        result.x.reshape(n_comp, N_PER_COMP)[:, 1],
        suppress=kwargs.get('suppress_positive_b_warning', False),
        stacklevel=3,
    )

    refined_ccurves = []
    for a_v, b_v, cinj_v in result.x.reshape(n_comp, N_PER_COMP):
        full_params = np.array([t0_fixed, u_fixed, a_v, b_v, e_fixed, Dz_fixed, cinj_v])
        refined_ccurves.append(EdmComponentCurve(x, full_params, model='cedm'))
    return refined_ccurves
