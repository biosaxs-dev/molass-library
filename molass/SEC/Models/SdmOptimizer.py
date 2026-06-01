"""
SEC.Models.SdmOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize
from molass.SEC.Models.SdmMonoPore import (
    sdm_monopore_pdf,
    sdm_monopore_gamma_pdf,
    DEFAULT_TIMESCALE,
)

def optimize_sdm_xr_decomposition(decomposition, env_params, model_params=None, **kwargs):
    """ Optimize the SDM decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    env_params : tuple
        The environmental parameters (N, T, me, mp, N0, t0, poresize).
    model_params : dict, optional
        The parameters for the SDM model.
    kwargs : dict
        Additional parameters for the optimization process.

    Returns
    -------
    new_xr_ccurves : list of SdmComponentCurve
        The optimized SDM component curves.
    """
    # N, T, N0, t0, poresize
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.SdmComponentCurve
        reload(molass.SEC.Models.SdmComponentCurve)
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve

    num_components = decomposition.num_components
    xr_icurve = decomposition.xr_icurve
    x, y = xr_icurve.get_xy()
    N, T, me, mp, N0, t0, poresize = env_params
    rgv = np.asarray(decomposition.get_rgs())

    # Quality-adaptive Rg anchoring: uses Guinier fit quality at each component's
    # peak frame to weight soft constraints in the objective and set hard-bound width.
    rgcurve = kwargs.get('rgcurve')
    rg_anchor_scale = model_params.get('rg_anchor_scale', 1.0) if model_params else 1.0
    rg_quality_threshold = model_params.get('rg_quality_threshold', 0.7) if model_params else 0.7
    if rgcurve is not None:
        jv_rg = np.array(rgcurve.frames)
        sc_rg = np.array(rgcurve.scores)
        rg_qualities = np.array([
            sc_rg[np.argmin(np.abs(jv_rg - int(c.x[c.y.argmax()])))]
            for c in decomposition.xr_ccurves
        ])
    else:
        rg_qualities = np.ones(num_components)

    if model_params is None:
        timescale = DEFAULT_TIMESCALE
        k_init = 2.0
        pore_dist = 'mono'
        rt_dist = 'gamma'
    else:
        timescale = model_params.get('timescale', DEFAULT_TIMESCALE)
        k_init = model_params.get('k', 2.0)
        pore_dist = model_params.get('pore_dist', 'mono')
        rt_dist = model_params.get('rt_dist', 'gamma')

    if rt_dist == 'exponential':
        k_init = 1.0   # not optimized for exponential
        _pdf_func = sdm_monopore_pdf
    else:
        _pdf_func = sdm_monopore_gamma_pdf

    def estimate_initial_scales():
        scales = []
        for rg in rgv:
            column = SdmColumn([N, T, me, mp, t0, t0, N0, poresize, timescale, k_init],
                               pore_dist=pore_dist, rt_dist=rt_dist)
            ccurve = SdmComponentCurve(x, column, rg, scale=1.0)
            cy = ccurve.get_y()
            idx = np.argmax(cy)
            scale = y[idx]/cy[idx] if cy[idx] > 0 else 1.0
            scales.append(scale)
        return scales

    # EGH peak frames are used as a soft position constraint in the objective.
    # Scale: ~1e-5 is enough to overcome the ~0.037 advantage of the degenerate solution
    # (where both components collapse to the same frame) over the separated solution.
    egh_peak_frames = np.array([c.x[c.y.argmax()] for c in decomposition.xr_ccurves], dtype=float)
    position_anchor_scale = model_params.get('position_anchor_scale', 1e-5) if model_params else 1e-5

    def objective_function(params, return_cy_list=False, plot=False):
        N_, T_, x0_, tI_, N0_, k_ = params[0:6]
        rgv_ = params[6:6+num_components]
        rg_diff = np.diff(rgv_)
        non_ordered = np.where(rg_diff > 0)[0]
        order_penalty = np.sum(rg_diff[non_ordered]**2) * 1e3  # penalty for non-ordered rgv
        # poresize is now an optimization variable (last in params vector)
        poresize_ = params[6+2*num_components]
        rhov = rgv_/poresize_
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0
        scales_ = params[6+num_components:6+2*num_components]
        cy_list = []
        x_ = x - tI_
        t0 = x0_ - tI_
        for rho, scale in zip(rhov, scales_):
            ni = N_*(1 - rho)**me
            ti = T_*(1 - rho)**mp
            if rt_dist == 'exponential':
                cy = scale * _pdf_func(x_, ni, ti, N0_, t0, timescale=timescale)
            else:
                theta = ti / k_  # Gamma scale: mean = k*theta = ti
                cy = scale * _pdf_func(x_, ni, k_, theta, N0_, t0, timescale=timescale)
            cy_list.append(cy)
        if return_cy_list:
            return cy_list
        ty = np.sum(cy_list, axis=0)
        if plot:
            import matplotlib.pyplot as plt
            plt.figure()
            plt.plot(x, y, label='Data')
            plt.plot(x, ty, label='Model')
            for i, cy in enumerate(cy_list):
                plt.plot(x, cy, label='Component %d' % (i+1))
            plt.legend()
            plt.show()
        # Quality-weighted soft Rg anchoring: pulls each component's Rg toward
        # its EGH-estimated value in proportion to the Guinier fit quality.
        # quality ≈ 1 → strong pull (stays near EGH Rg); quality ≈ 0 → unconstrained.
        rg_anchor_penalty = np.sum(rg_qualities * ((rgv_ / rgv - 1) ** 2)) * rg_anchor_scale
        # Position constraint: use theoretical centroid (mean of gamma, = x0 + N*T*(1-rho)^6)
        # which is amplitude-independent — prevents collapse to degenerate solution even
        # when one component's scale → 0. Peak position is the priority per user guidance.
        peak_positions = np.array([x0_ + N_ * (1-rho)**me * T_ * (1-rho)**mp for rho in rhov])
        position_penalty = np.sum((peak_positions - egh_peak_frames) ** 2) * position_anchor_scale
        error = np.sum((y - ty)**2) + order_penalty + rg_anchor_penalty + position_penalty
        return error

    # Void volume must precede every component peak — compute once, used for
    # both the physics-based starting point and the x0 upper bound.
    min_peak_frame = float(min(int(c.x[c.y.argmax()]) for c in decomposition.xr_ccurves))
    # x0_hi must precede all starting-point computations (both starts use it).
    x0_hi = min_peak_frame - 1

    # Estimator-based start (may be degenerate: t0 at upper bound → comp 0 vanishes)
    # Clamp to 1 frame inside the upper bound to avoid Nelder-Mead logit ±∞ at the boundary.
    t0_start = min(float(t0), x0_hi - 1.0)
    initial_guess = [N, T, t0_start, t0_start, N0, k_init]
    initial_guess += list(rgv)

    initial_scales = estimate_initial_scales()
    initial_guess += initial_scales
    initial_guess += [poresize]   # poresize as last parameter

    # Physics-based start: poresize=100 unlocks SEC-consistent Rg ordering.
    # With poresize=300 and Rg values ~29-33 Å, a 94-frame separation requires
    # x0 ≈ -1200 (infeasible). With poresize=100, the same separation fits with
    # x0=0 and swapped Rg ordering (earlier comp → larger Rg), which is physically
    # correct for SEC.
    poresize_physics = 100.0
    x0_physics = max(1.0, min_peak_frame * 0.001)  # stay 1 frame inside lower bound (avoids logit ±∞)
    peak_frames_phy = np.array([c.x[c.y.argmax()] for c in decomposition.xr_ccurves], dtype=float)
    rg_best_idx = int(np.argmax(rg_qualities))  # most reliable Rg (usually main peak)
    rho_best_phy = float(rgv[rg_best_idx]) / poresize_physics
    # Calibrate N*T from the reliable component's peak frame (using centroid formula):
    #   peak_frame ≈ x0 + N*T*(1-rho)^(me+mp)
    nt_physics = (peak_frames_phy[rg_best_idx] - x0_physics) / max((1 - rho_best_phy) ** (me + mp), 1e-6)
    N_physics = float(np.clip(nt_physics / 2.0, 100.0, 5000.0))   # T ≈ 2.0 as initial guess
    T_physics = float(np.clip(nt_physics / N_physics, 1e-3, 5.0))
    nt_actual = N_physics * T_physics
    # Derive Rg for each component from its target peak frame (centroid formula).
    # This may flip the Rg ordering vs EGH (earlier elution → larger Rg in SEC).
    rgv_physics = []
    for pf_phy in peak_frames_phy:
        target_frac = (pf_phy - x0_physics) / max(nt_actual, 1e-6)
        frac = float(np.clip(target_frac, 0.0, 0.9999))
        rho_derived = 1.0 - frac ** (1.0 / (me + mp))
        rg_derived = float(np.clip(rho_derived * poresize_physics, 1.0, poresize_physics * 0.99))
        rgv_physics.append(rg_derived)
    # Compute physics-specific scales
    physics_scales = []
    for rg_p in rgv_physics:
        column_p = SdmColumn([N_physics, T_physics, me, mp, x0_physics, x0_physics, N0, poresize_physics, timescale, k_init],
                             pore_dist=pore_dist, rt_dist=rt_dist)
        ccurve_p = SdmComponentCurve(x, column_p, rg_p, scale=1.0)
        cy_p = ccurve_p.get_y()
        idx_p = int(np.argmax(cy_p))
        physics_scales.append(float(y[idx_p] / cy_p[idx_p]) if cy_p[idx_p] > 0 else 1.0)
    physics_guess = [N_physics, T_physics, x0_physics, x0_physics, N0, k_init]
    physics_guess += rgv_physics
    physics_guess += physics_scales
    physics_guess += [poresize_physics]   # poresize as last parameter

    # objective_function(initial_guess, plot=True)
    if False:
        cy_list = objective_function(initial_guess, return_cy_list=True)
        for i, cy in enumerate(cy_list):
            idx = np.argmax(cy)
            scale = initial_scales[i]*y[idx]/cy[idx] if cy[idx] > 0 else initial_scales[i]
            initial_guess[6+num_components + i] = scale

    # The void volume (x0_) must precede every component peak — same constraint
    # as in the estimator. Without this bound, the optimizer drifts to the
    # degenerate solution: x0_ ≈ main-peak frame, ni*ti → 0.
    # (x0_hi already defined above, near min_peak_frame)
    # Set bounds for the parameters: N, T, x0, tI, N0, k
    bounds = [(100, 5000), (1e-3, 5), (0, x0_hi), (0, x0_hi), (500, 50000)]
    if rt_dist == 'exponential':
        bounds += [(0.999, 1.001)]   # k fixed at 1.0
    else:
        # Upper bound 2.0 prevents pathologically narrow peaks (k=10 → sigma≈6 frames
        # vs observed sigma≈25 frames for typical SEC data). For right-skewed SEC peaks,
        # k≈0.5–1.0 is physically appropriate; k=2.0 allows for nearly-symmetric peaks.
        bounds += [(0.5, 2.0)]       # k free for gamma
    # Tightly constrain the main component's Rg to preserve the column calibration anchor.
    # The main peak Rg is the most reliable (highest SNR Guinier analysis). Allowing it to
    # drift ±50% lets the SDM-predicted elution position shift, causing components to
    # converge to the wrong frame region. Other components keep the wide ±50% range.
    # Quality-adaptive Rg bounds: tight for reliable Rg estimates (backstop
    # for the soft penalty), wide for unreliable ones.
    rg_main_tol = model_params.get('rg_main_tol', 0.05) if model_params else 0.05
    rg_bounds = [
        (rg * (1 - rg_main_tol), rg * (1 + rg_main_tol)) if rg_qualities[i] >= rg_quality_threshold
        else (rg * 0.5, rg * 1.5)
        for i, rg in enumerate(rgv)
    ]
    bounds += rg_bounds
    upper_scale = xr_icurve.get_max_y() * 1000      # upper bounds for scales seem be large enough
    # Per-component scale lower bounds: 20% of physics_scales (SEC-consistent amplitude prior).
    # physics_scales are computed at poresize=100 where peak positions match the data, so
    # they represent well-grounded amplitude estimates. Using 20% prevents total collapse of a
    # component while allowing 5x downward amplitude flexibility from the physics estimate.
    # Also floor at 10% of the EGH-based initial_scale as a secondary guard.
    bounds += [(max(ps * 0.20, si * 0.10, 1e-15), upper_scale)
               for ps, si in zip(physics_scales, initial_scales)]
    # Restrict poresize to a tight range around the physics-derived value (100).
    # With poresize free in [75, 150] or [50, 500], the optimizer drifts to ≥150
    # (or 178) and collapses comp 0 to zero.  Bounding to ±10% of poresize_physics
    # prevents this by forcing the optimizer to find the SEC-consistent two-component
    # solution near poresize=100 where both components have physically motivated amplitudes.
    poresize_lo = poresize_physics * 0.9
    poresize_hi = poresize_physics * 1.1
    bounds += [(poresize_lo, poresize_hi)]   # tight range: ±10% of physics poresize
    # Clamp estimator poresize strictly inside [poresize_lo, poresize_hi].
    # The estimator may return poresize=300 (far above the bound). Starting at the
    # boundary causes logit ±∞ failure (same bug as the x0=0 case). Moreover, the
    # estimator's N/T/N0 are calibrated for its poresize (e.g. 300) — clamping to
    # a near-boundary value (e.g. 108.9) produces an inconsistent starting point
    # that triggers SDM formula overflow.  Reset to poresize_physics (midpoint of
    # bounds) which is guaranteed to be well-behaved.
    if not (poresize_lo * 1.01 <= initial_guess[-1] <= poresize_hi * 0.99):
        initial_guess[-1] = poresize_physics   # estimator poresize out of range → use physics value
    if model_params is None:
        method = None
    else:
        method = model_params.get('method', 'Nelder-Mead')
    # Multi-start: try both estimator-based and physics-based starting points;
    # keep whichever achieves the lower objective value.
    result = None
    start_names = ['estimator', 'physics']
    for i, (name, start) in enumerate(zip(start_names, [initial_guess, physics_guess])):
        r = minimize(objective_function, start, bounds=bounds, method=method)
        if debug:
            scales_i = r.x[6+num_components:6+2*num_components]
            poresize_i = r.x[6+2*num_components]
            print(f"  Start [{name}]: obj={r.fun:.6f}, scales={np.array2string(scales_i, precision=4)}, poresize={poresize_i:.1f}")
        if result is None or r.fun < result.fun:
            result = r

    if debug:
        print("Optimization success:", result.success)
        print("Optimized parameters: N=%g, T=%g, x0=%g, tI=%g, N0=%g, k=%g" % tuple(result.x[0:6]))
        print("Rgs:", result.x[6:6+num_components])
        print("Optimized poresize:", result.x[6+2*num_components])
        print("Rg qualities (anchoring weights):", rg_qualities)
        print("Physics-based start: x0=%g, N=%g, T=%g, poresize=%g, Rgs=%s"
              % (x0_physics, N_physics, T_physics, poresize_physics, str(rgv_physics)))
        print("physics_scales:", physics_scales)
        print("initial_scales:", initial_scales)
        print("scale lower bounds:", [max(ps*0.20, si*0.10, 1e-15) for ps, si in zip(physics_scales, initial_scales)])
        print("Objective function value:", result.fun)

    N_, T_, x0_, tI_, N0_, k_ = result.x[0:6]
    rgv_ = result.x[6:6+num_components]
    scales_ = result.x[6+num_components:6+2*num_components]
    poresize_ = result.x[6+2*num_components]

    # Post-NM NNLS rescaling: given the converged column shape, solve for optimal
    # scales analytically. NM may drift scales during joint shape exploration;
    # NNLS finds the exact 1D-fit optimum at the converged shape.
    from scipy.optimize import nnls as _nnls
    _rhov_ = np.clip(rgv_ / poresize_, 0.0, 1.0)
    _x_tI = x - tI_
    _t0_post = x0_ - tI_
    _A_cols = []
    for _rho in _rhov_:
        _ni = N_ * (1 - _rho) ** me
        _ti = T_ * (1 - _rho) ** mp
        if rt_dist == 'exponential':
            _cy = _pdf_func(_x_tI, _ni, _ti, N0_, _t0_post, timescale=timescale)
        else:
            _theta = _ti / k_
            _cy = _pdf_func(_x_tI, _ni, k_, _theta, N0_, _t0_post, timescale=timescale)
        _A_cols.append(_cy)
    _A_mat = np.array(_A_cols).T
    _scales_nnls, _ = _nnls(_A_mat, y)
    scales_ = np.array([max(s, 1e-3) for s in _scales_nnls])

    column = SdmColumn([N_, T_, me, mp, x0_, tI_, N0_, poresize_, timescale, k_],
                       pore_dist=pore_dist, rt_dist=rt_dist)
    print("initial_scales:", initial_scales)
    print("optimized scales_:", scales_)
    print("optimized k:", k_)
    new_xr_ccurves = []
    for rg, scale in zip(rgv_, scales_):
        ccurve = SdmComponentCurve(x, column, rg, scale)
        new_xr_ccurves.append(ccurve)
    return new_xr_ccurves

def optimize_sdm_uv_decomposition(decomposition, xr_ccurves, **kwargs):
    """ Optimize the SDM UV decomposition.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    xr_ccurves : list of SdmComponentCurve
        The SDM component curves from the XR decomposition.
    kwargs : dict
        Additional parameters for the optimization process.
        
    Returns
    -------
    new_uv_ccurves : list of UvComponentCurve
        The optimized UV component curves.
    """
    debug = kwargs.get('debug', False)
    from molass.Mapping.Mapping import Mapping
    if debug:
        from importlib import reload
        import molass.SEC.Models.UvComponentCurve
        reload(molass.SEC.Models.UvComponentCurve)
    from .UvComponentCurve import UvComponentCurve

    num_components = decomposition.num_components
    x, y = decomposition.uv_icurve.get_xy()

    def objective_function(params):
        a_, b_ = params[0:2]
        mapping = Mapping(a_, b_)
        scales_ = params[2:2+num_components]
        cy_list = []
        for xr_ccurve, scale in zip(xr_ccurves, scales_):
            uv_ccurve = UvComponentCurve(x, mapping, xr_ccurve, scale)
            cy = uv_ccurve.get_y()
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        error = np.sum((y - ty)**2)
        return error

    mapping = decomposition.mapping
    a, b = mapping.slope, mapping.intercept

    initial_guess = [a, b] + [1.0]*num_components
    dx = (x[-1] - x[0])*0.1
    bounds = [(a*0.8, a*1.2), (b-dx, b+dx)] + [(1e-3, 10.0) for _ in range(num_components)]
    result = minimize(objective_function, initial_guess, bounds=bounds)

    new_mapping = Mapping(*result.x[0:2])
    new_uv_ccurves = []
    for xr_ccurve, scale in zip(xr_ccurves, result.x[2:]):
        ccurve = UvComponentCurve(x, new_mapping, xr_ccurve, scale)
        new_uv_ccurves.append(ccurve)
    return new_uv_ccurves


def optimize_sdm_lognormal_xr_decomposition(decomposition, env_params, model_params=None, **kwargs):
    """Optimize XR decomposition with SDM lognormal pore distribution.

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition to optimize.
    env_params : tuple
        The environmental parameters ``(N, T, me, mp, N0, t0, mu, sigma)``.
    model_params : dict, optional
        The parameters for the SDM model.  Recognized keys:

        ``ln_pore_sigma`` : float or None (default 0.3)
            Standard deviation of ``ln(r/r0)``, held constant during
            optimization (removed from the free-parameter vector).
            Invariant to the choice of length unit (a unit change only
            shifts all ``ln(r/r0)`` values by a constant, which drops out
            of the standard deviation).
            The default 0.3 implies pores span a factor of
            ``exp(0.3) ≈ 1.35`` around the median — a reasonable prior for
            most SEC columns.  Pass ``None`` to make sigma a free parameter;
            note that sigma is underdetermined when ``num_components=1``
            and will drift to ``sigma_max`` if left free.
        ``sigma_max`` : float (default 0.8)
            Upper bound on sigma when it is free.
        ``k`` : float (default 2.0)
        ``rt_dist`` : str (default ``'gamma'``)
    kwargs : dict
        Additional parameters for the optimization process.

    Returns
    -------
    new_xr_ccurves : list of SdmComponentCurve
        The optimized SDM component curves with lognormal pore distribution.
    """
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.SEC.Models.SdmComponentCurve
        reload(molass.SEC.Models.SdmComponentCurve)
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve
    from molass.SEC.Models.LognormalPore import sdm_lognormal_pore_gamma_pdf_fast

    num_components = decomposition.num_components
    xr_icurve = decomposition.xr_icurve
    x, y = xr_icurve.get_xy()
    N, T, me, mp, N0, t0, mu_init, sigma_init = env_params
    rgv = np.asarray(decomposition.get_rgs())

    # ln_pore_sigma default: 0.3 — std-dev of ln(r/r0), invariant to unit choice.
    # Free sigma (None) is underdetermined for num_components=1 and drifts to sigma_max.
    _LN_PORE_SIGMA_DEFAULT = 0.3
    if model_params is None:
        k_init = 2.0
        rt_dist = 'gamma'
        rg_penalty_weight = 1.0
        sigma_max = 0.8
        min_rg_gap = 0.5
        ln_pore_sigma = _LN_PORE_SIGMA_DEFAULT
        nm_maxiter = None
    else:
        k_init = model_params.get('k', 2.0)
        rt_dist = model_params.get('rt_dist', 'gamma')
        rg_penalty_weight = model_params.get('rg_penalty_weight', 1.0)
        sigma_max = model_params.get('sigma_max', 0.8)
        min_rg_gap = model_params.get('min_rg_gap', 0.5)  # Å — minimum required Rg gap between components
        ln_pore_sigma = model_params.get('ln_pore_sigma', _LN_PORE_SIGMA_DEFAULT)
        nm_maxiter = model_params.get('maxiter', None)

    if rt_dist == 'exponential':
        k_init = 1.0

    # Estimate initial scales using NNLS (non-negative least squares).
    # The previous peak-ratio method (y[argmax]/cy[argmax]) fails when the model
    # curve peaks at a location where data is negative, producing negative/huge
    # scales that clip to the lower bound and prevent NM from recovering (Issue #108).
    from scipy.optimize import nnls as _nnls
    A_cols = []
    for rg in rgv:
        column = SdmColumn([N, T, me, mp, t0, t0, N0, mu_init, sigma_init, k_init],
                           pore_dist='lognormal', rt_dist=rt_dist)
        ccurve = SdmComponentCurve(x, column, rg, scale=1.0)
        A_cols.append(ccurve.get_y())
    A_mat = np.array(A_cols).T  # (n_frames, n_components)
    scales_nnls, _ = _nnls(A_mat, y)
    scales_init = [max(s, 0.01) for s in scales_nnls]

    # Compute initial data-fit error for Rg penalty calibration
    cy_init_list = []
    for rg, scale in zip(rgv, scales_init):
        column = SdmColumn([N, T, me, mp, t0, t0, N0, mu_init, sigma_init, k_init],
                           pore_dist='lognormal', rt_dist=rt_dist)
        ccurve = SdmComponentCurve(x, column, rg, scale)
        cy_init_list.append(ccurve.get_y())
    ty_init = np.sum(cy_init_list, axis=0)
    initial_error = np.sum((y - ty_init) ** 2)
    # Rg penalty scale: initial_error means 100% relative deviation costs ~initial_error
    rg_penalty_scale = rg_penalty_weight * initial_error

    def objective_function(params):
        N_, T_, x0_, tI_, N0_, k_, mu_ = params[0:7]
        if ln_pore_sigma is None:
            sigma_ = params[7]
            rgv_start = 8
        else:
            sigma_ = ln_pore_sigma
            rgv_start = 7
        rgv_ = params[rgv_start:rgv_start + num_components]
        scales_ = params[rgv_start + num_components:rgv_start + 2 * num_components]

        if sigma_ < 0.01 or sigma_ > sigma_max:
            return 1e20
        if mu_ < 1.0 or mu_ > 8.0:
            return 1e20

        # Rg ordering penalty (Rg should be descending)
        rg_diff = np.diff(rgv_)   # negative when ordered: rg_diff = rg[i+1] - rg[i] < 0
        non_ordered = np.where(rg_diff > 0)[0]
        order_penalty = np.sum(rg_diff[non_ordered] ** 2) * 1e3

        # Minimum Rg gap penalty — prevents components collapsing to identical curves.
        # For descending order: -rg_diff should be >= min_rg_gap.
        # Penalty ∝ (shortfall)² when the gap is insufficient (Issue #180).
        if min_rg_gap > 0 and num_components > 1:
            shortfall = min_rg_gap + rg_diff   # positive where -rg_diff < min_rg_gap
            insufficient = shortfall[shortfall > 0]
            gap_penalty = np.sum(insufficient ** 2) * rg_penalty_scale * 100
        else:
            gap_penalty = 0.0

        x_ = x - tI_
        t0_ = x0_ - tI_
        cy_list = []
        for rg_, scale_ in zip(rgv_, scales_):
            cy = scale_ * sdm_lognormal_pore_gamma_pdf_fast(
                x_, 1.0, N_, T_, k_, me, mp, mu_, sigma_, rg_, N0_, t0_
            )
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        # Penalize Rg deviation from Guinier values (prevents Rg drift in lognormal model)
        rg_penalty = rg_penalty_scale * np.sum(((rgv_ - rgv) / rgv) ** 2)
        error = np.sum((y - ty) ** 2) + order_penalty + rg_penalty + gap_penalty
        _eval_count[0] += 1
        n = _eval_count[0]
        if debug and n % 50 == 0:
            print(f"  lognormal opt: {n} evals, error={error:.4g}", flush=True)
        return error

    _eval_count = [0]

    # Initial guess: [N, T, x0, tI, N0, k, mu, (sigma if free), ...Rg, ...scale]
    initial_guess = [N, T, t0, t0, N0, k_init, mu_init]
    if ln_pore_sigma is None:
        initial_guess += [sigma_init]
    initial_guess += list(rgv)
    initial_guess += scales_init

    # Bounds
    bounds = [
        (100, 5000),              # N
        (1e-3, 5),                # T
        (t0 - 1000, t0 + 1000),  # x0
        (t0 - 1000, t0 + 1000),  # tI
        (500, 50000),             # N0
    ]
    if rt_dist == 'exponential':
        bounds += [(0.999, 1.001)]  # k fixed at 1.0
    else:
        bounds += [(0.5, 10.0)]     # k free for gamma
    bounds += [(2.0, 8.0)]          # mu
    if ln_pore_sigma is None:
        bounds += [(0.01, sigma_max)]    # sigma — upper bound prevents degenerate flat curves (Issue #180)
    bounds += [(rg * 0.5, rg * 1.5) for rg in rgv]
    upper_scale = xr_icurve.get_max_y() * 1000
    bounds += [(1e-3, upper_scale) for _ in range(num_components)]

    method = 'Nelder-Mead'
    if model_params is not None:
        method = model_params.get('method', 'Nelder-Mead')

    # Clip initial guess to bounds to avoid OptimizeWarning (Issue #108)
    initial_guess = np.array(initial_guess, dtype=float)
    for i, (lo, hi) in enumerate(bounds):
        initial_guess[i] = np.clip(initial_guess[i], lo, hi)

    # Lognormal has more parameters than mono-pore and needs more iterations
    # to converge. Default NM maxiter (200*N) is insufficient (Issue #108).
    # nm_maxiter can be reduced via model_params={'maxiter': N} for quick init passes.
    n_params = len(initial_guess)
    nm_options = {'maxiter': nm_maxiter if nm_maxiter is not None else max(200 * n_params, 12000)}

    result = minimize(objective_function, initial_guess, bounds=bounds,
                      method=method, options=nm_options)

    import warnings as _warnings
    N_, T_, x0_, tI_, N0_, k_, mu_ = result.x[0:7]
    if ln_pore_sigma is None:
        sigma_ = result.x[7]
        rgv_start = 8
    else:
        sigma_ = ln_pore_sigma
        rgv_start = 7
    rgv_ = result.x[rgv_start:rgv_start + num_components]
    scales_ = result.x[rgv_start + num_components:rgv_start + 2 * num_components]

    # Post-NM NNLS rescaling: given the converged column shape, solve for optimal
    # scales analytically. NM may drift scales during joint shape exploration;
    # NNLS finds the exact 1D-fit optimum at the converged shape.
    _x_tI = x - tI_
    _t0_post = x0_ - tI_
    _A_cols = []
    for _rg in rgv_:
        _cy = sdm_lognormal_pore_gamma_pdf_fast(
            _x_tI, 1.0, N_, T_, k_, me, mp, mu_, sigma_, _rg, N0_, _t0_post)
        _A_cols.append(_cy)
    _A_mat = np.array(_A_cols).T
    _scales_nnls, _ = _nnls(_A_mat, y)
    scales_ = np.array([max(s, 1e-3) for s in _scales_nnls])

    if debug:
        print(f"Lognormal optimization: {_eval_count[0]} evals, success={result.success}")
        sigma_str = f"{sigma_:.4f}(fixed)" if ln_pore_sigma is not None else f"{sigma_:.4f}"
        print(f"N={N_:.4g}, T={T_:.4g}, x0={x0_:.4g}, tI={tI_:.4g}, N0={N0_:.4g}, k={k_:.4g}, mu={mu_:.4g}, sigma={sigma_str}")
        print("Rgs:", rgv_)
        print("Scales:", scales_)
        print(f"Rg initial (Guinier): {rgv}")
        print(f"Rg penalty weight: {rg_penalty_weight}, initial_error: {initial_error:.4g}")

    # Warn when sigma is close to its upper bound — indicates a near-degenerate
    # solution where the optimizer could not separate the components properly.
    # This typically happens when the dataset has only one dominant species.
    # Skip when sigma was fixed by the caller — user explicitly chose a constant.
    if ln_pore_sigma is None and sigma_ > sigma_max * 0.9:
        _warnings.warn(
            f"SDM(lognormal) optimizer converged at sigma={sigma_:.4f} (sigma_max={sigma_max}). "
            "The two components may have collapsed to near-identical pore distributions. "
            "Check plot_components() and consider using pore_dist='mono' or "
            "reducing num_components to 1.",
            UserWarning, stacklevel=3
        )

    column = SdmColumn([N_, T_, me, mp, x0_, tI_, N0_, mu_, sigma_, k_],
                       pore_dist='lognormal', rt_dist=rt_dist)

    if debug:
        print("initial_scales:", scales_init)
        print("optimized scales:", list(scales_))
        print("optimized k:", k_)
        sigma_str = f"{sigma_:.4f}(fixed)" if ln_pore_sigma is not None else f"{sigma_:.4f}"
        print("optimized mu:", mu_, "sigma:", sigma_str)

    new_xr_ccurves = []
    for rg, scale in zip(rgv_, scales_):
        ccurve = SdmComponentCurve(x, column, rg, scale)
        new_xr_ccurves.append(ccurve)

    # Guard: check that the resulting C matrix is not near-singular (Issue #180).
    # A degenerate C (cond >> 1) means pinv(C) amplifies noise catastrophically,
    # making the extracted scattering profiles P = M @ pinv(C) numerically garbage
    # and causing Guinier analysis to fail inside plot_components().
    if num_components > 1:
        C_mat = np.array([cc.get_y() for cc in new_xr_ccurves])
        cond_C = np.linalg.cond(C_mat)
        if cond_C > 1e6:
            pore_opt = np.exp(mu_)
            rg_max_val = float(np.max(rgv_))
            pore_safe = 2.0 * rg_max_val
            pore_hint = (
                f" Optimized pore center: {pore_opt:.1f} Å (mu={mu_:.3f})."
                f" SDM separation requires pore ≤ 2×Rg_max = {pore_safe:.1f} Å;"
                f" above this, K_SEC values compress and elution curves converge."
                f" Try constraining the moment-matching bound to"
                f" mu_max = ln({pore_safe:.1f}) = {np.log(pore_safe):.4f}."
            ) if pore_opt > pore_safe else ""
            raise RuntimeError(
                f"SDM(lognormal) produced a degenerate decomposition "
                f"(C condition number = {cond_C:.2e}, sigma = {sigma_:.4f}). "
                "The component elution curves are nearly identical; "
                "P = M @ pinv(C) would be numerically meaningless."
                + pore_hint +
                " Other suggested actions: use pore_dist='mono', or reduce num_components to 1."
            )

    return new_xr_ccurves

def adjust_rg_and_poresize(sdm_decomposition):
    """ Adjust rg and poresize in the decomposition based on the optimized component curves.
    """
    from .SdmComponentCurve import SdmColumn
    rgs = np.array(sdm_decomposition.get_rgs())     # get SAXS rgs
    xr_ccurves = sdm_decomposition.xr_ccurves
    column = xr_ccurves[0].column
    column_params = column.get_params()
    # params: (N, T, me, mp, x0, tI, N0, poresize, timescale, k)
    poresize = column_params[7]
    rhov = []
    for i, ccurve in enumerate(xr_ccurves):
        rg = ccurve.rg
        rho = min(1, rg/poresize)
        rhov.append(rho)
    rhov = np.array(rhov)

    def posize_adjustment_error(poresize_):
        model_rgv = rhov * poresize_
        error = np.sum((model_rgv - rgs)**2)   # sum of squared differences (not square of sum)
        return error
    
    result = minimize(posize_adjustment_error, poresize, bounds=[(poresize*0.5, poresize*1.5)])
    new_poresize = result.x[0]
    print("Adjusted poresize from %g to %g" % (poresize, new_poresize))

    new_column_params = list(column_params)
    new_column_params[7] = new_poresize
    new_column = SdmColumn(new_column_params, pore_dist=column.pore_dist, rt_dist=column.rt_dist)
    for i, ccurve in enumerate(xr_ccurves):
        ccurve.column = new_column
        ccurve.rg = rhov[i] * new_poresize
        



 