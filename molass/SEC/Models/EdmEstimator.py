"""
SEC.Models.EdmEstimator.py
"""
import numpy as np
from scipy.optimize import minimize

def estimate_edm_init_params(decomposition, **kwargs):
    """
    Estimate column parameters from the initial curve and component curves.

    N, T, N0, t0, poresize

    Parameters
    ----------
    decomposition : Decomposition
        The decomposition containing the initial curve and component curves.
    kwargs : dict
        Additional parameters for the estimation process.
        
        **Automatic bounds derivation** (new in v0.8.x):
        If ``a_bounds``, ``b_bounds``, or ``cinj_min`` are not explicitly
        provided in kwargs, they are automatically derived from the EGH
        decomposition parameters via
        :func:`~molass.SEC.Models.EdmRecommend.suggest_cedm_bounds_from_egh`.
        
        To disable auto-bounds and use unconstrained optimization, pass
        ``auto_bounds=False``.
        
    Returns
    -------
    (N, T, N0, t0, poresize) : tuple
        Estimated parameters for the EDM column.
    """
    debug = kwargs.get('debug', False)
    
    # --- Auto-derive bounds from EGH parameters (unless user specified) ---
    auto_bounds = kwargs.get('auto_bounds', True)
    if auto_bounds and decomposition.model == 'egh':
        # Check which bounds are missing
        needs_bounds = (
            'a_bounds' not in kwargs or
            'b_bounds' not in kwargs or
            'cinj_min' not in kwargs
        )
        if needs_bounds:
            if debug:
                from importlib import reload
                import molass.SEC.Models.EdmRecommend
                reload(molass.SEC.Models.EdmRecommend)
            from molass.SEC.Models.EdmRecommend import suggest_cedm_bounds_from_egh
            
            suggested = suggest_cedm_bounds_from_egh(
                decomposition,
                e_assumed=kwargs.get('e_assumed', 0.5),
                verbose=debug
            )
            
            # Merge suggested bounds into kwargs (user-specified takes precedence)
            kwargs.setdefault('a_bounds', suggested['a_bounds'])
            kwargs.setdefault('b_bounds', suggested['b_bounds'])
            kwargs.setdefault('cinj_min', suggested['cinj_min'])
            # Note: shared_b is advisory only; not auto-applied yet
    
    if debug:
        from importlib import reload
        import molass.SEC.Models.EdmEstimatorImpl
        reload(molass.SEC.Models.EdmEstimatorImpl)
    from molass.SEC.Models.EdmEstimatorImpl import guess_multiple_impl

    xr_icurve = decomposition.xr_icurve
    x, y = xr_icurve.get_xy()
    xr_params = guess_multiple_impl(x, y, decomposition.xr_ccurves, debug=debug)
    return xr_params