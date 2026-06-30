"""
SEC.Models.EdmRecommend.py

Derive CEDM parameter bounds from well-fitted EGH decomposition.
"""
import numpy as np


def suggest_cedm_bounds_from_egh(decomp_egh, e_assumed=0.5, verbose=False):
    """
    Derive CEDM parameter bounds from fitted EGH decomposition.
    
    This function analyzes the EGH peak positions, asymmetry (tau), and
    relative heights to recommend physically plausible bounds for CEDM
    parameters (a, b, cinj), preventing optimizer collapse to degenerate
    solutions.
    
    Parameters
    ----------
    decomp_egh : Decomposition
        EGH decomposition with well-fitted parameters. Must have `.xr_ccurves`
        with EGH component curves (each with ``.params`` returning
        ``[H, tR, sigma, tau]``).
    e_assumed : float, optional
        Assumed porosity for analytical ``a`` (K_SEC) calculation. Default 0.5
        (typical SEC total porosity). Used to convert EGH retention times to
        K_SEC range estimates.
    verbose : bool, optional
        If True, print diagnostic information about derived bounds. Default False.
    
    Returns
    -------
    dict
        Dictionary with the following keys:
        
        - ``'a_bounds'``: tuple (a_min, a_max)
            Lower and upper bounds for partition coefficient ``a`` (K_SEC).
            Derived from EGH peak positions with 2× safety margin.
        
        - ``'b_bounds'``: tuple (b_min, b_max)
            Lower and upper bounds for adsorption exponent ``b``.
            Derived from EGH asymmetry (tau):
            
            - ``|tau| < 0.3`` (nearly symmetric) → ``(-2.0, 0.5)`` (mostly kinetic)
            - ``tau < -0.3`` (right-tail) → ``(-5.0, 1.0)``
            - ``tau > 0.3`` (left-tail, unusual) → ``(-1.0, 3.0)``
        
        - ``'cinj_min'``: float
            Minimum injection concentration (prevents component collapse).
            Set to 15% of weakest component's relative height, floor at 0.15.
        
        - ``'shared_b'``: bool
            Recommendation for whether to share ``b`` across components.
            True if EGH tau values are similar (std < 0.2), indicating
            column-property behavior rather than molecule-specific.
        
        - ``'a_analytical'``: list of float
            Analytical K_SEC values computed from EGH retention times
            (for reference/debugging).
    
    Notes
    -----
    **Integration with upgrade()**:
        These bounds are automatically applied when calling
        ``decomposition.upgrade(model='EDM')`` unless explicitly overridden
        via kwargs (e.g., ``a_bounds=(0, 3.0)`` in the call).
    
    **Physical Interpretation**:
        - **a (K_SEC)**: Partition coefficient between mobile and stationary phases.
          For SEC, K_SEC = accessible_pore_volume / mobile_phase_volume.
          Typical range: 0.0 (total exclusion) to 1.5 (full access).
        
        - **b**: Adsorption isotherm exponent. In SEC, tailing is normally
          kinetic (b ≈ 0), not adsorptive (b > 0). Positive b suggests
          secondary adsorption or overloading.
        
        - **cinj**: Injection concentration. Prevents optimizer from collapsing
          components to zero amplitude (degenerate solution).
    
    Examples
    --------
    >>> decomp_egh = corrected.quick_decomposition(proportions=[1, 1])
    >>> bounds = suggest_cedm_bounds_from_egh(decomp_egh, verbose=True)
    >>> # Bounds are auto-applied:
    >>> decomp_edm = decomp_egh.upgrade(model='EDM')
    >>> # Or explicitly override:
    >>> decomp_edm = decomp_egh.upgrade(model='EDM', a_bounds=(0, 2.5))
    """
    # Extract EGH parameters: [H, tR, sigma, tau]
    egh_params = np.array([cc.get_params() for cc in decomp_egh.xr_ccurves])
    heights = egh_params[:, 0]
    tR_values = egh_params[:, 1]
    tau_values = egh_params[:, 3]
    
    tR_min, tR_max = tR_values.min(), tR_values.max()
    tau_mean = tau_values.mean()
    tau_std = tau_values.std()
    
    # --- 1. Derive a_bounds from retention times ---
    # CEDM retention: tR_i = t0 + (L/u) * (1 + a_i * F), F = (1-e)/e
    L_EDM = 30.0  # hardcoded in edm_impl
    
    # Analytical t0 and u (same logic as EdmOptimizer.py shared_column init)
    t0_analytical = tR_min * 0.9  # assume void slightly before first peak
    peak_delay = tR_min - t0_analytical
    if peak_delay <= 0:
        peak_delay = 1.0  # guard
    void_time = peak_delay / 1.1  # leave 10% headroom
    u_analytical = L_EDM / void_time
    
    # Phase ratio F = Vp/V0 = (1-e)/e
    F_assumed = (1 - e_assumed) / e_assumed
    
    # Solve for a: a_i = [(tR_i - t0) / (L/u) - 1] / F
    # Equivalent: a_i = [(tR_i - t0) * u / L - 1] / F
    a_analytical = []
    for tR in tR_values:
        a_val = ((tR - t0_analytical) * u_analytical / L_EDM - 1) / max(F_assumed, 1e-3)
        a_analytical.append(max(a_val, 0.0))  # K_SEC non-negative
    
    a_max = 2.0 * max(a_analytical)  # 2× safety margin
    a_bounds = (0.0, a_max)
    
    # --- 2. Derive b_bounds from tau asymmetry ---
    # tau > 0: right-tail (kinetic tailing, b < 0 typical for SEC)
    # tau < 0: left-tail (Langmuir adsorption, b > 0, unusual in SEC)
    # tau ≈ 0: Gaussian (b ≈ 0)
    
    if abs(tau_mean) < 0.3:
        # Nearly symmetric peaks → mostly kinetic tailing
        b_bounds = (-2.0, 0.5)
    elif tau_mean > 0:
        # Right-tail dominant (typical SEC kinetic limitation)
        b_bounds = (-5.0, 1.0)
    else:
        # Left-tail (unusual; secondary adsorption or overloading)
        b_bounds = (-1.0, 3.0)
    
    # Recommend sharing b if tau values are similar (column property)
    shared_b = (tau_std < 0.2)
    
    # --- 3. Derive cinj_min from relative heights ---
    # Prevent collapse: require each component to be at least 15% of weakest
    # component's EGH height
    height_min = heights.min()
    height_mean = heights.mean()
    cinj_min = 0.15 * (height_min / height_mean)
    cinj_min = max(0.15, cinj_min)  # absolute floor
    
    if verbose:
        print("=== CEDM Bounds from EGH ===")
        print(f"  EGH retention times: {tR_values}")
        print(f"  Analytical a values: {a_analytical}")
        print(f"  → a_bounds: {a_bounds}")
        print(f"  EGH tau (asymmetry): mean={tau_mean:.3f}, std={tau_std:.3f}")
        print(f"  → b_bounds: {b_bounds}, shared_b={shared_b}")
        print(f"  EGH heights: {heights}")
        print(f"  → cinj_min: {cinj_min:.3f}")
    
    return {
        'a_bounds': a_bounds,
        'b_bounds': b_bounds,
        'cinj_min': cinj_min,
        'shared_b': shared_b,
        'a_analytical': a_analytical,
    }
