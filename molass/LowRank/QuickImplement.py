"""
LowRank.QuickImplement
"""
import numpy as np
from importlib import reload
from molass.Decompose.XrOnlyUtils import make_dummy_uv_ccurves

def make_decomposition_impl(ssd, num_components=None, **kwargs):    
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.CoupledAdjuster
        reload(molass.LowRank.CoupledAdjuster)
    from molass.LowRank.CoupledAdjuster import make_component_curves

    requested_num_components = num_components
    proportions = kwargs.pop('proportions', None)
    xr_peakpositions = kwargs.pop('xr_peakpositions', None)
    if proportions is not None and xr_peakpositions is not None:
        raise ValueError("Cannot specify both 'proportions' and 'xr_peakpositions'.")

    if xr_peakpositions is not None:
        if num_components is None:
            num_components = len(xr_peakpositions)
        else:
            assert num_components == len(xr_peakpositions), "num_components must equal len(xr_peakpositions)."
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves_with_positions(ssd, num_components, xr_peakpositions, **kwargs)
    elif proportions is not None:
        if num_components is None:
            num_components = len(proportions)
        else:
            assert num_components == len(proportions), "num_components must be equal to the length of proportions."
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves_with_proportions(ssd, num_components, proportions, **kwargs)
    else:
        xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves(ssd, num_components, **kwargs)

    if debug:
        import molass.LowRank.Decomposition
        reload(molass.LowRank.Decomposition)
    from molass.LowRank.Decomposition import Decomposition

    if len(xr_ccurves) == 0:
        raise ValueError(
            "Auto-detection found 0 components. The data may have insufficient signal. "
            "Try specifying num_components explicitly."
        )

    warn_on_suspicious_components(requested_num_components, xr_ccurves,
                                  allow_negative=kwargs.get('allow_negative_peaks', False))

    if uv_ccurves is None:
        uv_ccurves = make_dummy_uv_ccurves(ssd, xr_ccurves)

    decomposition = Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)
    decomposition.method_label = "quick decomposition"
    warn_on_implausible_component_rg(ssd, decomposition)
    return decomposition

NEGLIGIBLE_SHARE = 1e-3
# a component Rg outside [RG_LOWER_FACTOR * min, RG_UPPER_FACTOR * max] of the reliable data Rg is flagged (#372)
RG_LOWER_FACTOR = 0.5
RG_UPPER_FACTOR = 2.0
RG_SAMPLE_FRAMES = 9
RG_SAMPLE_INTENSITY_FRAC = 0.3
RG_SAMPLE_MIN_SCORE = 0.6


def data_rg_range(ssd, xr_icurve):
    """(min, max) of the reliable data Rg, or None if it cannot be told.

    Uses the Rg curve if ``ssd`` already holds one; otherwise Guinier fits at a few
    (``RG_SAMPLE_FRAMES``) frames spread over the elution where the intensity is at least
    ``RG_SAMPLE_INTENSITY_FRAC`` of the maximum, which costs about a second instead of the
    seconds-to-minutes of the whole curve.
    """
    rgcurve = getattr(ssd, '_rgcurve', None)
    if rgcurve is not None:
        intensity = np.interp(rgcurve.frames, xr_icurve.x, xr_icurve.y)
        _, rgs = rgcurve.reliable(score_min=RG_SAMPLE_MIN_SCORE, intensity=intensity,
                                  intensity_frac=RG_SAMPLE_INTENSITY_FRAC)
        return (float(np.min(rgs)), float(np.max(rgs))) if len(rgs) >= 3 else None

    from molass.Guinier.RgEstimator import RgEstimator
    y = np.asarray(xr_icurve.y, dtype=float)
    ok = np.flatnonzero(y >= RG_SAMPLE_INTENSITY_FRAC*np.max(y))
    if len(ok) < 3:
        return None
    picks = ok[np.unique(np.linspace(0, len(ok) - 1, RG_SAMPLE_FRAMES).round().astype(int))]
    xr = ssd.xr
    jv = np.asarray(xr.jv)
    rgs = []
    for i in picks:
        j = int(np.searchsorted(jv, xr_icurve.x[i]))
        if j >= len(jv) or jv[j] != xr_icurve.x[i]:
            continue
        sg = RgEstimator(np.array([xr.qv, xr.M[:, j], xr.E[:, j]]).T)
        if sg.Rg is not None and np.isfinite(sg.Rg) and sg.Rg > 0 and sg.score >= RG_SAMPLE_MIN_SCORE:
            rgs.append(float(sg.Rg))
    return (min(rgs), max(rgs)) if len(rgs) >= 3 else None


def warn_on_implausible_component_rg(ssd, decomposition):
    """Warn (molass-library#372) when a component's Guinier Rg is missing or far outside the data Rg.

    A component whose Rg is below ``RG_LOWER_FACTOR`` times the smallest or above ``RG_UPPER_FACTOR``
    times the largest reliable data Rg (``data_rg_range``) does not describe the sample: typically a
    degenerate decomposition of a continuum with the default proportions. The check never raises.
    """
    import warnings
    try:
        components = decomposition.get_xr_components()
        rgs = []
        for c in components:
            rg = c.get_guinier_object().Rg
            rgs.append(None if rg is None or not np.isfinite(rg) or rg <= 0 else float(rg))
        span = data_rg_range(ssd, decomposition.xr_icurve)
    except Exception:
        return
    bad = []
    for i, rg in enumerate(rgs, start=1):
        if rg is None:
            bad.append((i, "no Guinier Rg"))
        elif span is not None and not (RG_LOWER_FACTOR*span[0] <= rg <= RG_UPPER_FACTOR*span[1]):
            bad.append((i, f"Rg={rg:.1f}"))
    if not bad:
        return
    where = "" if span is None else f"; the data Rg is {span[0]:.0f}-{span[1]:.0f} (reliable frames)"
    warnings.warn(
        f"component(s) {', '.join(f'{i} ({what})' for i, what in bad)} look physically implausible{where}. "
        f"The decomposition may be degenerate (e.g. a continuum or overlapping peaks with the default "
        f"proportions): try proportions=[1]*k or a different num_components.",
        UserWarning, stacklevel=4)

def warn_on_suspicious_components(requested, xr_ccurves, allow_negative=False):
    """Warn (molass-library#321) when the result silently differs from what was asked for.

    1. Fewer components than requested: peak recognition found fewer peaks.
    2. A component with a non-positive or negligible area share: its per-component
       results (Guinier I0, I0/UV ratios, ...) are meaningless.

    The warnings point at the caller of ``quick_decomposition``.
    """
    import warnings

    n = len(xr_ccurves)
    if requested is not None and n < requested:
        warnings.warn(
            f"quick_decomposition(num_components={requested}) returned {n} components: "
            f"peak recognition found only {n} peaks. To get {requested} components, "
            f"pass proportions=[1]*{requested} (proportional slicing) or "
            f"xr_peakpositions=[...] with {requested} frame positions.",
            UserWarning, stacklevel=4)

    if allow_negative or n == 0:
        return
    areas = np.array([np.sum(c.get_y()) for c in xr_ccurves], dtype=float)
    total = np.sum(areas)
    if total <= 0:
        return
    shares = areas/total
    bad = [i + 1 for i, (a, s) in enumerate(zip(areas, shares)) if a <= 0 or s < NEGLIGIBLE_SHARE]
    if bad:
        details = ", ".join(f"{i}: {shares[i-1]:.2g}" for i in bad)
        warnings.warn(
            f"component(s) {bad} have a non-positive or negligible area share ({details}); "
            f"their per-component results (e.g. Guinier I0, I0/UV ratios) are not meaningful. "
            f"Try a different num_components or different xr_peakpositions/proportions.",
            UserWarning, stacklevel=4)

def make_component_curves_with_proportions(ssd, num_components, proportions, **kwargs):
    """
    Make component curves with given proportions.

    Parameters
    ----------
    ssd : SecSaxsData
        The SecSaxsData object containing the data.
    num_components : int
        The number of components to decompose into.
    proportions : list of float
        The proportions for each component.
    xslices : list of slice, optional (via kwargs)
        Precomputed slices over the XR icurve's x-axis, passed through to
        decompose_proportionally() -- see molass.Decompose.Proportional for
        cross-channel slicing (e.g. deriving boundaries from the UV icurve).
    proportions_source : {'xr', 'uv'}, optional (via kwargs)
        Which channel's icurve the proportional fit runs on. Default ``'xr'`` (original
        behavior: fit on XR, then derive UV as XR's partner). ``'uv'`` instead fits fully
        on the UV icurve (usually much better signal-to-noise for small features) and
        derives XR as UV's partner -- see molass.Decompose.UvFirst. XR remains the primary
        shape source used by the rest of the pipeline either way; this only changes which
        channel the proportional *fit* is performed against.
    """

    assert len(proportions) == num_components, "Length of proportions must be equal to num_components."
    proportions = np.asarray(proportions)
    assert np.all(proportions >= 0), "All proportions must be non-negative."
    assert np.sum(proportions) > 0, "Sum of proportions must be positive."
    proportions = proportions/np.sum(proportions)

    debug = kwargs.get('debug', False)

    if kwargs.get('proportions_source', 'xr') == 'uv':
        if debug:
            import molass.Decompose.UvFirst
            reload(molass.Decompose.UvFirst)
        from molass.Decompose.UvFirst import make_component_curves_with_uv_proportions
        allow_negative = kwargs.get('allow_negative_peaks', False)
        num_plates = kwargs.get('num_plates', None)
        return make_component_curves_with_uv_proportions(ssd, num_components, proportions, debug=debug,
                                                           allow_negative_peaks=allow_negative, num_plates=num_plates)

    if debug:
        import molass.Decompose.Proportional
        reload(molass.Decompose.Proportional)
        import molass.Decompose.Partner
        reload(molass.Decompose.Partner)
    from molass.Decompose.Proportional import decompose_proportionally
    from molass.Decompose.RgOrder import RgOrderPenalty, DEFAULT_RG_ORDER_WEIGHT
    from molass.Decompose.Partner import decompose_from_partner
    from molass.LowRank.ComponentCurve import ComponentCurve

    def get_curves_from_params(result_params, icurve):
        ret_curves = []
        for params in result_params.reshape((num_components, 4)):
            ret_curves.append(ComponentCurve(icurve.x, params))
        return ret_curves

    # Create XR curves
    xr_icurve = ssd.xr.get_icurve()
    allow_negative = kwargs.get('allow_negative_peaks', False)
    num_plates = kwargs.get('num_plates', None)
    xslices = kwargs.get('xslices', None)
    rg_order = None
    rg_order_weight = kwargs.get('rg_order_weight', DEFAULT_RG_ORDER_WEIGHT)
    if rg_order_weight > 0 and not allow_negative and ssd.xr.M.shape[1] == len(xr_icurve.x):
        rg_order = RgOrderPenalty(ssd.xr.M, ssd.xr.qv, num_components, weight=rg_order_weight)
        if not rg_order.enabled:
            rg_order = None
    xr_result = decompose_proportionally(xr_icurve, proportions, debug=debug, allow_negative_peaks=allow_negative, num_plates=num_plates, xslices=xslices, rg_order=rg_order)
    xr_ccurves = get_curves_from_params(xr_result.x, xr_icurve)

    # Create UV curves
    if ssd.has_uv():
        uv_icurve = ssd.uv.get_icurve()
        mapping = ssd.get_mapping()
        uv_ccurves = decompose_from_partner(uv_icurve, mapping, xr_ccurves, debug=debug)
    else:
        uv_icurve = None
        uv_ccurves = make_dummy_uv_ccurves(ssd, xr_ccurves)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves

def make_component_curves_with_positions(ssd, num_components, xr_peakpositions, **kwargs):
    """
    Make component curves with peak positions pinned to specified frame numbers.

    Parameters
    ----------
    ssd : SecSaxsData
        The SecSaxsData object containing the data.
    num_components : int
        The number of components to decompose into.
    xr_peakpositions : list of float
        The frame positions for each peak.
    """
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.PositionedDecomposer
        reload(molass.LowRank.PositionedDecomposer)
        import molass.Decompose.Partner
        reload(molass.Decompose.Partner)
    from molass.LowRank.PositionedDecomposer import decompose_icurve_positioned
    from molass.Decompose.Partner import decompose_from_partner
    from molass.LowRank.ComponentCurve import ComponentCurve

    decompargs = {
        'peakpositions': list(xr_peakpositions),
        'tau_limit': kwargs.pop('tau_limit', 0.6),
        'max_sigma': kwargs.pop('max_sigma', 80),
        'min_sigma': kwargs.pop('min_sigma', 5),
    }

    # Create XR curves
    xr_icurve = ssd.xr.get_icurve()
    x, y = xr_icurve.get_xy()
    params = decompose_icurve_positioned(x, y, decompargs, debug=debug)
    xr_ccurves = [ComponentCurve(xr_icurve.x, params[i]) for i in range(num_components)]

    # Create UV curves
    if ssd.has_uv():
        uv_icurve = ssd.uv.get_icurve()
        mapping = ssd.get_mapping()
        uv_ccurves = decompose_from_partner(uv_icurve, mapping, xr_ccurves, debug=debug)
    else:
        uv_icurve = None
        uv_ccurves = make_dummy_uv_ccurves(ssd, xr_ccurves)

    return xr_icurve, xr_ccurves, uv_icurve, uv_ccurves
