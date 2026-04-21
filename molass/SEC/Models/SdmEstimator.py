"""
SEC.Models.SdmEstimator.py
"""
import numpy as np
from scipy.optimize import minimize

def estimate_sdm_column_params(decomposition, **kwargs):
    """
    Estimate column parameters from the initial curve and component curves.

    N, T, me, mp, N0, t0, poresize

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition containing the initial curve and component curves.
    poresize_bounds : (lo, hi) tuple, optional
        Bounds for the column pore size in Å. Default: (70, 300).
        Use a narrow window when the column type is known
        (e.g., (75, 80) for Superdex 200).
    N0 : float, optional
        If given, the mobile-phase plate number is **fixed** to this value
        and excluded from the optimization. Use when N0 is known from
        buffer-only runs.
    N0_bounds : (lo, hi) tuple, optional
        Bounds for N0 when it is a free parameter. Default: (500, 50000).
        Ignored if ``N0`` is given.
    include_M3 : bool, optional
        If True (default), include the third central moment (cube-root
        skewness) in the matching objective. This is critical for
        asymmetric peaks; for symmetric peaks it is a near no-op.
        Set False to reproduce the legacy M1+M2-only behaviour.
    M1_weight, M2_weight, M3_weight : float, optional
        Weights for the moment-matching objective.
        Defaults follow legacy ``DispersiveMonopore.guess_params_using_moments``:
        M1=6.0, M2=2.0, M3=2.0.
    debug : bool, optional
        If True, print diagnostics and show a debug plot.

    Returns
    -------
    (N, T, me, mp, N0, t0, poresize) : tuple
        Estimated parameters for the SDM column.
    """
    debug = kwargs.get('debug', False)
    poresize_bounds = kwargs.get('poresize_bounds', (70, 300))
    N0_fixed = kwargs.get('N0', None)
    N0_bounds = kwargs.get('N0_bounds', (500, 50000))
    include_M3 = kwargs.get('include_M3', True)
    W1 = kwargs.get('M1_weight', 6.0)
    W2 = kwargs.get('M2_weight', 2.0)
    W3 = kwargs.get('M3_weight', 2.0)

    rgv = np.asarray(decomposition.get_rgs())
    xr_ccurves = decomposition.xr_ccurves

    # Per-component target moments: (M1, std, sk^(1/3))
    # Note: the legacy implementation uses cube-root skew (sign-preserving) so
    # that the M3 term is on the same length scale as M1 and std.
    moment_list = []
    for ccurve in xr_ccurves:
        cx, cy = ccurve.get_xy()
        y_pos = np.maximum(cy, 0)
        W = y_pos.sum()
        m1 = (cx * y_pos).sum() / W
        m2c = (y_pos * (cx - m1)**2).sum() / W
        m3c = (y_pos * (cx - m1)**3).sum() / W
        std = np.sqrt(max(m2c, 1e-12))
        sk3 = np.sign(m3c) * abs(m3c)**(1/3)
        moment_list.append((m1, std, sk3))

    me = 1.5
    mp = 1.5

    # Pack parameter vector. Layout depends on whether N0 is fixed.
    #   N0 free  → params = [N, T, N0, t0, poresize]
    #   N0 fixed → params = [N, T,     t0, poresize]
    def unpack(params):
        if N0_fixed is None:
            N, T, N0_, t0, poresize = params
        else:
            N, T, t0, poresize = params
            N0_ = N0_fixed
        return N, T, N0_, t0, poresize

    def objective_function(params, return_moments=False):
        N, T, N0_, t0, poresize = unpack(params)
        rhov = rgv/poresize
        rhov[rhov > 1] = 1.0  # limit rhov to 1.0

        error = 0.0
        if return_moments:
            modeled_moments = []
        for (m1_t, std_t, sk3_t), rho in zip(moment_list, rhov):
            ni = N*(1 - rho)**me
            ti = T*(1 - rho)**mp
            model_mean = t0 + ni*ti
            model_var = 2*ni*ti**2 + model_mean**2/N0_
            model_std = np.sqrt(max(model_var, 1e-12))
            term = W1*(m1_t - model_mean)**2 + W2*(std_t - model_std)**2
            if include_M3:
                # SDM monopore third central moment (legacy formula)
                M3 = 6*ni*ti**2*(N0_*ti + ni*ti + t0)/N0_
                model_sk3 = np.sign(M3) * abs(M3)**(1/3)
                term += W3*(sk3_t - model_sk3)**2
            error += term
            if return_moments:
                modeled_moments.append((model_mean, model_var))
        if return_moments:
            return modeled_moments
        return error

    # Multi-start search: this objective has two basins (symmetric: large
    # poresize / small T;  asymmetric: small poresize / large T). The M3 term
    # discriminates between them but a single Nelder-Mead start often gets
    # trapped in the wrong one. Sweep a few poresize starts and keep the best.
    # See issue #111 discussion.
    lo, hi = poresize_bounds
    if N0_fixed is None:
        bounds = [(100, 5000), (1e-3, 5), N0_bounds, (-1000, 1000), poresize_bounds]
        def make_init(ps):
            return [500, 1.0, 10000, 0, ps]
    else:
        bounds = [(100, 5000), (1e-3, 5), (-1000, 1000), poresize_bounds]
        def make_init(ps):
            return [500, 1.0, 0, ps]

    poresize_starts = sorted(set([
        lo + 0.1*(hi - lo),
        lo + 0.3*(hi - lo),
        lo + 0.5*(hi - lo),
        lo + 0.7*(hi - lo),
        lo + 0.9*(hi - lo),
    ]))
    best_result = None
    for ps0 in poresize_starts:
        r = minimize(objective_function, make_init(ps0), bounds=bounds,
                     method='Nelder-Mead',
                     options=dict(xatol=1e-4, fatol=1e-8, maxiter=20000))
        if best_result is None or r.fun < best_result.fun:
            best_result = r
    result = best_result
    N, T, N0_out, t0, poresize = unpack(result.x)
    if debug:
        import matplotlib.pyplot as plt
        print("Rgs:", rgv)
        print("Optimization success:", result.success)
        print("Estimated parameters: N=%g, T=%g, N0=%g, t0=%g, poresize=%g"
              % (N, T, N0_out, t0, poresize))
        print("Objective function value:", result.fun)
        x, y = decomposition.xr_icurve.get_xy()
        modeled_moments = objective_function(result.x, return_moments=True)
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(x, y, label='Initial Curve')
        for i, ccurve in enumerate(decomposition.xr_ccurves):
            mean, std, _ = moment_list[i]
            ax.axvline(mean, color='gray', linestyle='--', label=f'Component {i+1} Mean')
            ax.fill_betweenx([0, max(y)], mean - std, mean + std, color='gray', alpha=0.3, label=f'Component {i+1} Std Dev')
            modeled_mean, modeled_var = modeled_moments[i]
            modeled_std = np.sqrt(modeled_var)
            ax.axvline(modeled_mean, color='blue', linestyle='--', label=f'Modeled Component {i+1} Mean')
            ax.fill_betweenx([0, max(y)], modeled_mean - modeled_std, modeled_mean + modeled_std, color='blue', alpha=0.3, label=f'Modeled Component {i+1} Std Dev')
            cx, cy = ccurve.get_xy()
            ax.plot(cx, cy, label=f'Component {i+1}')
        ax.legend()
        plt.show()
    return N, T, me, mp, N0_out, t0, poresize


def estimate_sdm_lognormal_column_params(decomposition, **kwargs):
    """
    Estimate column parameters for SDM with lognormal pore distribution.

    Runs the mono-pore estimator first, then converts poresize to
    lognormal parameters (mu, sigma).

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition containing the initial curve and component curves.
    kwargs : dict
        Additional parameters for the estimation process.

    Returns
    -------
    (N, T, me, mp, N0, t0, mu, sigma) : tuple
        Estimated parameters for the SDM column with lognormal pore distribution.
    """
    N, T, me, mp, N0, t0, poresize = estimate_sdm_column_params(decomposition, **kwargs)
    mu = np.log(poresize)
    sigma = 0.3  # initial breadth for optimizer to refine
    return N, T, me, mp, N0, t0, mu, sigma


def estimate_sdm_lognormal_from_monopore(mono_ccurves, xr_icurve, **kwargs):
    """
    Estimate lognormal column parameters from converged mono-pore SDM results.

    Converts the mono-pore column parameters to lognormal initial guess by:
    1. Extracting converged (N, T, x0, tI, N0, k) from the mono-pore result
    2. Setting mu = ln(geometric_mean(poresize_stored, 2.5*Rg_max)), sigma=0.3
    3. Shifting x0/tI to align the lognormal PDF peak with the data peak
    4. (Optional) Refining (t0, k, mu, sigma) by analytical moment matching
       against the EGH decomposition. Enabled when ``decomposition`` is given.

    Parameters
    ----------
    mono_ccurves : list of SdmComponentCurve
        Converged mono-pore component curves.
    xr_icurve : Curve
        The XR integrated elution curve (data).
    decomposition : Decomposition, optional
        EGH decomposition. When provided, the heuristic init is refined by
        moment matching (see ``refine_lognormal_params_by_moments``).
        Recommended for the standard SDM(lognormal) pipeline.
    debug : bool, optional
    moment_refine : bool, optional
        If False, skip the moment-matching refinement step even when
        ``decomposition`` is given. Default True.

    Returns
    -------
    (N, T, me, mp, N0, t0_adj, mu, sigma) : tuple
        Estimated parameters for the lognormal SDM optimizer.
    """
    from .SdmComponentCurve import SdmColumn, SdmComponentCurve

    debug = kwargs.get('debug', False)
    column = mono_ccurves[0].column
    N, T, me, mp, x0, tI, N0, poresize_stored, timescale, k = column.get_params()

    # Use the mono-pore's stored poresize as the lognormal center,
    # but scale it down. The mono-pore estimator's poresize (~171 Å) is the
    # exclusion limit; for a lognormal distribution center, a smaller value
    # works better as starting point. The 2.5*Rg heuristic was too small (~81 Å)
    # and caused 85× worse initial fit, but poresize_stored was too large and
    # led the optimizer into a bad basin (Rg hitting bounds).
    # Geometric mean of the two gives a balanced starting point.
    rg_max = max(cc.rg for cc in mono_ccurves)
    rg_based = 2.5 * rg_max
    effective_poresize = np.sqrt(poresize_stored * rg_based)
    mu = np.log(effective_poresize)
    sigma = 0.3

    # Create a test lognormal PDF with the dominant component to find peak position
    x_data, y_data = xr_icurve.get_xy()
    rg_dominant = mono_ccurves[0].rg
    col_test = SdmColumn([N, T, me, mp, x0, tI, N0, mu, sigma, k],
                         pore_dist='lognormal', rt_dist=column.rt_dist)
    cc_test = SdmComponentCurve(x_data, col_test, rg_dominant, scale=1.0)
    cy_test = cc_test.get_y()
    pdf_peak = x_data[np.argmax(cy_test)]
    data_peak = x_data[np.argmax(y_data)]
    shift = data_peak - pdf_peak

    # t0 for the optimizer (sets both x0 and tI to this value initially)
    t0_adj = x0 + shift

    if debug:
        print(f"Lognormal from mono-pore: poresize_stored={poresize_stored:.1f}, rg_based={rg_based:.1f}")
        print(f"  effective_poresize={effective_poresize:.1f} (geometric mean), mu={mu:.4f}")
        print(f"  PDF peak={pdf_peak:.0f}, data peak={data_peak:.0f}, shift={shift:.0f}")
        print(f"  x0: {x0:.1f} → {x0 + shift:.1f}, t0_adj={t0_adj:.1f}")

    # Optional: refine (t0, k, mu, sigma) by moment matching against EGH.
    # Significantly improves init quality when EGH decomposition is available.
    decomposition = kwargs.get('decomposition', None)
    moment_refine = kwargs.get('moment_refine', True)
    if decomposition is not None and moment_refine:
        t0_adj, k, mu, sigma = refine_lognormal_params_by_moments(
            decomposition, N, T, N0, t0_adj, k, mu, sigma,
            me=me, mp=mp, debug=debug)

    return N, T, me, mp, N0, t0_adj, mu, sigma


def refine_lognormal_params_by_moments(
        decomposition, N, T, N0, t0, k, mu, sigma, me=1.5, mp=1.5,
        debug=False):
    """Refine SDM lognormal column parameters by analytical moment matching.

    Given an initial guess (typically from ``estimate_sdm_lognormal_from_monopore``
    which uses heuristic poresize geometric mean + sigma=0.3), this function
    refines (mu, sigma, k, t0) by L-BFGS-B against the per-component (M1, Var)
    extracted from the EGH decomposition.

    Uses the fast analytical moment evaluator
    :func:`molass.SEC.Models.LognormalPore.sdm_lognormal_model_moments`
    (~50 us/call), so the full refinement (~100 evals × num_components) costs
    only a few ms.

    Only (mu, sigma, k, t0) are refined; (N, T, N0) are held fixed because
    the mono-pore stage already constrains them well from M1+M2+M3 matching.

    Parameters
    ----------
    decomposition : Decomposition
        EGH decomposition providing per-component empirical moments.
    N, T, N0, t0, k, mu, sigma : float
        Initial guesses (from ``estimate_sdm_lognormal_from_monopore``).
    me, mp : float, optional
        SEC partition exponents (default 1.5).
    debug : bool, optional
        If True, print per-component moment-matching diagnostics.

    Returns
    -------
    (t0, k, mu, sigma) : tuple of float
        Refined parameters. Other inputs (N, T, N0) are returned by the caller.

    See Also
    --------
    molass.SEC.Models.LognormalPore.sdm_lognormal_model_moments
    """
    from molass.SEC.Models.LognormalPore import sdm_lognormal_model_moments

    rgv = np.asarray(decomposition.get_rgs())

    # Per-component empirical moments (M1 = mean, M2 = variance)
    target_moments = []
    for ccurve in decomposition.xr_ccurves:
        cx, cy = ccurve.get_xy()
        y_pos = np.maximum(cy, 0.0)
        W = y_pos.sum()
        if W <= 0:
            continue
        M1 = (cx * y_pos).sum() / W
        Var = (y_pos * (cx - M1)**2).sum() / W
        target_moments.append((M1, Var))

    if not target_moments:
        return t0, k, mu, sigma

    # Component proportions for weighting (larger components dominate the fit)
    areas = np.array([np.maximum(cc.get_xy()[1], 0).sum()
                      for cc in decomposition.xr_ccurves])
    props = areas / areas.sum()

    eps = 1e-30

    def objective(params):
        t0_, k_, mu_, sigma_ = params
        err = 0.0
        for i, (M1_t, Var_t) in enumerate(target_moments):
            M1_m, Var_m = sdm_lognormal_model_moments(
                rgv[i], N, T, N0, t0_, k_, mu_, sigma_, me=me, mp=mp)
            # log-sum keeps the M1 (~hundreds) and Var (~thousands) terms
            # on comparable scales without manual weighting
            err += props[i] * (
                np.log((M1_m - M1_t)**2 + eps)
                + np.log((Var_m - Var_t)**2 + eps)
            )
        return err

    bounds = [
        (t0 - 500, t0 + 500),       # t0
        (max(0.5, k * 0.3), max(10.0, k * 3)),   # k
        (max(2.0, mu - 1.0), min(7.0, mu + 1.0)),   # mu
        (0.05, 1.5),                # sigma
    ]
    x0 = [t0, k, mu, sigma]

    result = minimize(objective, x0, method='L-BFGS-B', bounds=bounds)
    t0_r, k_r, mu_r, sigma_r = result.x

    if debug:
        print("=== refine_lognormal_params_by_moments ===")
        print(f"  Init:    t0={t0:.1f}, k={k:.3f}, mu={mu:.3f}, sigma={sigma:.3f}")
        print(f"  Refined: t0={t0_r:.1f}, k={k_r:.3f}, mu={mu_r:.3f}, sigma={sigma_r:.3f}")
        print(f"  poresize (median): {np.exp(mu):.1f} -> {np.exp(mu_r):.1f}")
        print(f"  Objective: {result.fun:.4g} (success={result.success})")
        for i, (M1_t, Var_t) in enumerate(target_moments):
            M1_m, Var_m = sdm_lognormal_model_moments(
                rgv[i], N, T, N0, t0_r, k_r, mu_r, sigma_r, me=me, mp=mp)
            print(f"  Comp {i} (Rg={rgv[i]:.1f}):")
            print(f"    M1: target={M1_t:.2f}, model={M1_m:.2f}, dM={M1_m-M1_t:+.2f}")
            print(f"    Var: target={Var_t:.3f}, model={Var_m:.3f}, dV={Var_m-Var_t:+.3f}")

    return t0_r, k_r, mu_r, sigma_r