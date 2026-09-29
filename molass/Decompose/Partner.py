"""
Decompose.Partner.py
"""

import logging
import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

VERY_SMALL_VALUE = 1e-10

def map_params_to_partner(icurve, mapping, source_params, inverse=False):
    """
    Map classic EGH params (H, tR, sigma, tau) from one curve's frame axis onto
    `icurve`'s frame axis, keeping shape (tR, sigma, tau) fixed under the affine mapping
    and refitting only the per-component heights jointly against `icurve`'s own data.

    This is the shared core of decompose_from_partner() (the default, XR-shape-to-UV
    direction) -- factored out so the same "map shape, refit heights only" logic can also
    run in reverse (UV-shape-to-XR), for cases where UV has much better signal-to-noise
    for small features than XR (see molass-library issue #270,
    Decompose.UvFirst.make_component_curves_with_uv_proportions()). The XR-first flow
    remains the default/primary path; this only adds a reusable, direction-agnostic
    primitive.

    Parameters
    ----------
    icurve : Curve
        The target curve; only its data (not its shape) drives the height refit.
    mapping : MappingInfo
        slope/intercept affine mapping between XR and UV frame axes.
    source_params : array-like, shape (n, 4)
        Source (H, tR, sigma, tau) params, in the SOURCE curve's frame units.
    inverse : bool, optional
        False (default): source is XR, target (`icurve`) is UV --
        ``tR_uv = slope * tR_xr + intercept``.
        True: source is UV, target (`icurve`) is XR --
        ``tR_xr = (tR_uv - intercept) / slope``.

    Returns
    -------
    initial_params, refit_params : ndarray, ndarray
        Both shape (n, 4), in `icurve`'s frame units. `initial_params` uses `icurve`'s
        spline value at the mapped tR as a first height guess (pre-refit); `refit_params`
        has heights jointly optimized against `icurve`'s actual data (shape unchanged).
        Heights are hard-bounded via molass.Decompose.RatioBounds.compute_ratio_bounds()
        applied to the initial height/source-height ratios, so a weak component can no
        longer collapse toward zero or flip sign during the refit (molass-library#271).
    """
    from molass.SEC.Models.Simple import egh
    from molass.Decompose.RatioBounds import compute_ratio_bounds

    source_params = np.asarray(source_params)
    if inverse:
        tR = mapping.uv_to_xr(source_params[:, 1])
        scale_factor = 1.0 / mapping.slope
    else:
        tR = mapping.xr_to_uv(source_params[:, 1])
        scale_factor = mapping.slope
    sigma = source_params[:, 2] * scale_factor
    tau = source_params[:, 3] * scale_factor

    spline = icurve.get_spline()
    H0 = spline(tR)
    initial_params = np.column_stack([H0, tR, sigma, tau])

    source_H = source_params[:, 0]
    init_ratios = H0 / np.maximum(np.abs(source_H), 1e-10)
    lower_ratio, upper_ratio = compute_ratio_bounds(init_ratios)
    bounds = [(sh * lower_ratio, sh * upper_ratio) if sh > 0 else (0.0, sh * upper_ratio)
              for sh in np.abs(source_H)]
    # L-BFGS-B expects x0 within bounds -- H0 (data-driven, unbounded) can fall outside
    # the just-computed band, e.g. for a weak/noisy component.
    x0 = np.array([min(max(h, lo), hi) for h, (lo, hi) in zip(H0, bounds)])

    x, y = icurve.get_xy()
    def objective(heights):
        y_fit = np.zeros_like(y)
        for h, tR_, sigma_, tau_ in zip(heights, tR, sigma, tau):
            y_fit += egh(x, h, tR_, sigma_, tau_)
        return np.sum((y - y_fit) ** 2)

    result = minimize(objective, x0, bounds=bounds)
    refit_params = np.column_stack([result.x, tR, sigma, tau])

    return initial_params, refit_params

def decompose_from_partner(icurve, mapping, xr_ccurves, debug=False):
    """
    Guess initial parameters for decomposition based on partner parameters.

    Parameters
    ----------
    icurve : Curve
        The intensity elution curve to be decomposed.
    mapping : MappingInfo
        The mapping information to convert partner parameters to current data parameters.
    xr_ccurves : list of ComponentCurve
        The list of XR component curves to extract partner parameters from.
    debug : bool, optional
        If True, enable debug mode, by default False.    

    Returns
    -------
    initial_params : array-like
        The guessed initial parameters for the egh function: (height, mean, std, tau).
    """
    if debug:
        print("Decompose.Partner.decompose_from_partner: reload modules for debug")
        from importlib import reload
        import molass.SEC.Models.UvComponentCurve
        reload(molass.SEC.Models.UvComponentCurve)
    from molass.SEC.Models.UvComponentCurve import UvComponentCurve
    from molass.Mapping.Mapping import Mapping

    source_params = np.array([ccurve.get_params() for ccurve in xr_ccurves])
    initial_params, temp_params = map_params_to_partner(icurve, mapping, source_params, inverse=False)

    if debug:
        from molass.SEC.Models.Simple import egh
        import matplotlib.pyplot as plt
        x, y = icurve.get_xy()
        fig, axes = plt.subplots(ncols=2, figsize=(12,5))
        fig.suptitle("Decompose from Partner")
        for title, ax, plot_params in [("Initial Parameters", axes[0], initial_params),
                                       ("Optimized Parameters", axes[1], temp_params)]:
            ax.set_title(title)
            ax.plot(x, y, color='gray', alpha=0.5)
            for p in plot_params:
                ax.plot(x, egh(x, *p), linestyle=':')
        fig.tight_layout()
        plt.show()

    # uv_ccurves
    a, b = mapping.slope, mapping.intercept
    mapping_ = Mapping(a, b)    # task: make clear the difference between mapping and mapping_
    x, _ = icurve.get_xy()
    uv_ccurves = []
    for i, xr_ccurve in enumerate(xr_ccurves):
        scale = temp_params[i, 0]
        xr_h = xr_ccurve.get_params()[0]
        # degenerate (near-zero height) XR component, e.g. from an empty proportional slice:
        # xr_ccurve.get_y() is ~0 everywhere too, so a zero ratio is the consistent fallback
        if abs(xr_h) > VERY_SMALL_VALUE:
            ratio = scale / xr_h
        else:
            ratio = 0.0
            logger.debug("decompose_from_partner: component %d has near-zero xr_h=%g; "
                         "falling back to ratio=0.0", len(uv_ccurves), xr_h)
        uv_ccurves.append(UvComponentCurve(x, mapping_, xr_ccurve, ratio))

    return uv_ccurves