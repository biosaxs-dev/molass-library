"""
SEC.Models.UvOptimizer.py
"""
import numpy as np
from scipy.optimize import minimize

def optimize_uv_decomposition(decomposition, xr_ccurves, **kwargs):
    """ Optimize the UV decomposition based on the given XR component curves.

    Parameters
    ----------
    decomposition : Decomposition
        The initial decomposition containing the UV initial curve and component curves.
    xr_ccurves : list of UvComponentCurve
        The XR component curves to be used for UV optimization.
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

    # Physics-based initial scale: ratio of UV to XR amplitude at XR component peak.
    # Avoids the fixed-scale=1.0 local minimum that arises when model tails create
    # Hessian cross-coupling (observed: SDM minor component, MY dataset, May 2026).
    initial_scales = []
    for xr_ccurve in xr_ccurves:
        peak_xr_idx = int(np.argmax(xr_ccurve.y))
        peak_xr_val = float(xr_ccurve.y[peak_xr_idx])
        peak_xr_frame = float(xr_ccurve.x[peak_xr_idx])
        # mapping converts XR frame → UV frame (a*xr + b = uv)
        peak_uv_frame = a * peak_xr_frame + b
        uv_idx = int(np.argmin(np.abs(x - peak_uv_frame)))
        uv_val = float(y[uv_idx])
        s0 = uv_val / peak_xr_val if peak_xr_val > 0 else 1.0
        initial_scales.append(float(max(s0, 1e-3)))   # no upper clip — ratio can exceed 10

    if debug:
        scale_str = '[' + ', '.join(f'{s:.3g}' for s in initial_scales) + ']'
        print(f'[UV] initial_guess: a={a:.4g}  b={b:.4g}  scales={scale_str}')

    initial_guess = [a, b] + initial_scales
    dx = (x[-1] - x[0])*0.1
    # Upper bound: 3× the largest initial scale estimate (data-driven, not hard-wired).
    # The old hard-coded 10.0 cap was too tight when UV/XR amplitude ratio > 10
    # (e.g. UV ≈ 14 OD, XR ≈ 0.5 counts → ratio ≈ 28), causing optimized scales
    # to saturate at the bound and uv_params to appear "too small".
    upper_scale = max(initial_scales) * 3.0
    bounds = [(a*0.8, a*1.2), (b-dx, b+dx)] + [(1e-3, upper_scale) for _ in range(num_components)]
    result = minimize(objective_function, initial_guess, bounds=bounds)

    if debug:
        converged_scales = list(result.x[2:])
        residual_rms = float(np.sqrt(result.fun / len(y))) if len(y) > 0 else float('nan')
        scale_str = '[' + ', '.join(f'{s:.3g}' for s in converged_scales) + ']'
        print(f'[UV] converged:     a={result.x[0]:.4g}  b={result.x[1]:.4g}  scales={scale_str}  residual_rms={residual_rms:.4g}')

    new_mapping = Mapping(*result.x[0:2])
    new_uv_ccurves = []
    for xr_ccurve, scale in zip(xr_ccurves, result.x[2:]):
        ccurve = UvComponentCurve(x, new_mapping, xr_ccurve, scale)
        new_uv_ccurves.append(ccurve)
    return new_uv_ccurves
