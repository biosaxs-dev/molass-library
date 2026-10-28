"""
    Trimming.UsableQrange.py
"""
class UsableQrange:
    """
    Holds information about the usable Q range in XR data.

    Attributes
    ----------
    start : int
        The starting index of the usable Q range.
    stop : int
        The stopping index of the usable Q range.
    icurve : ICurve
        The intensity curve associated with the XR data.
    pre_rg : PreliminaryRg
        The preliminary Rg information associated with the XR data.
    """
    def __init__(self, start, stop, icurve, pre_rg):
        """ 
        Parameters
        ----------
        start : int
            The starting index of the usable Q range.
        stop : int
            The stopping index of the usable Q range.
        icurve : ICurve
            The intensity curve associated with the XR data.
        pre_rg : PreliminaryRg
            The preliminary Rg information associated with the XR data.
        """
        self.start = start
        self.stop = stop
        self.icurve = icurve
        self.pre_rg = pre_rg

SMALL_ANGLE_LIMITS = ('extended', 'guinier', 'none')

# the legacy GUI defaults (molass_legacy SerialSettings: acceptable_rg_consist, use_bqlimit, force_bqlimit)
ACCEPTABLE_RG_CONSISTENCY = 0.8


def _extended_small_angle_start(xr_data):
    """Start of the angular range as the legacy GUI sets it by default ("Extended Limit beyond the
    Guinier Q range" plus the B(q) limit), i.e. keeping more low-q points than the Guinier start.

    Returns None if the computation fails (the caller then falls back to the Guinier start).
    """
    import io
    import logging
    import warnings
    from contextlib import redirect_stdout
    import numpy as np
    try:
        from molass_legacy.SerialAnalyzer.ElutionCurve import ElutionCurve
        from molass_legacy.Trimming.FlangeLimit import FlangeLimit
        from molass_legacy.Trimming.PreliminaryRg import PreliminaryRg
        from molass_legacy.Trimming.GuinierLimit import GuinierLimit
        from molass_legacy.Trimming.CdLimit import CdLimit
        D, E, qv = xr_data.M, xr_data.E, xr_data.qv
        x, y = xr_data.get_icurve().get_xy()
        with redirect_stdout(io.StringIO()), warnings.catch_warnings():
            warnings.simplefilter('ignore')     # the legacy limits log() of non-positive extrapolations
            ecurve = ElutionCurve(y)
            flange = FlangeLimit(D, E, ecurve, qv).get_limit()
            pre_rg = PreliminaryRg(D, E, ecurve, qv, flange)
            qlimit = int(np.argmin(np.abs(qv - xr_data.pickat)))
            try:
                start = GuinierLimit(D, ecurve, pre_rg, qlimit).get_limit(ACCEPTABLE_RG_CONSISTENCY)
            except Exception:
                start = 0
            try:
                b_limit, _ = CdLimit(D, E, ecurve, qv).get_limit()
                if b_limit > start:
                    start = b_limit
            except Exception:
                pass
        return int(start)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "the extended small-angle limit could not be computed (%s: %s); using the Guinier start",
            type(exc).__name__, exc)
        return None


def get_usable_qrange_impl(xr_data, ip_effect_info=False, nguiniers=None, return_object=False, debug=False,
                           small_angle_limit=None):
    """
    Get the usable Q range for the given XR data.

    Parameters
    ----------
    xr_data : XRData
        The XR data to analyze.
    ip_effect_info : bool
        Whether to consider inter-particle effects.
    nguiniers : int or None
        Number of Guinier points to consider. If None, use default.
    return_object : bool
        If True, return a UsableQrange object. If False, return (start, stop).
    debug : bool
        If True, enable debug mode.
    small_angle_limit : {'extended', 'guinier', 'none'} or None
        How the start (small-angle side) of the range is determined, as in the legacy GUI's
        "Guinier Limit in Small Angle Data Trimming":

        - ``'extended'``: extended limit beyond the Guinier range (Rg-consistency 0.8) and the B(q)
          limit; keeps more low-q points, which is where interparticle effects act.
        - ``'guinier'``: the minimum of the Guinier range (the behaviour before molass-library#342).
        - ``'none'``: the minimum of the measured q range.

        If None, the global option ``small_angle_limit`` is used.

    Returns
    -------
    UsableQrange or (int, int)
        The usable Q range as a UsableQrange object or as (start, stop) tuple.
    """
    if small_angle_limit is None:
        from molass.Global.Options import get_molass_options
        small_angle_limit = get_molass_options('small_angle_limit')
    if small_angle_limit not in SMALL_ANGLE_LIMITS:
        raise ValueError(f"small_angle_limit must be one of {SMALL_ANGLE_LIMITS}, not {small_angle_limit!r}")
    if debug:
        from importlib import reload
        import molass.Legacy.BackCompatUtils
        reload(molass.Legacy.BackCompatUtils)
    from molass.Legacy.BackCompatUtils import ElutioCurvProxy
    from molass_legacy.Trimming.FlangeLimit import FlangeLimit
    from molass_legacy.Trimming.PreliminaryRg import PreliminaryRg
    xr_icurve = xr_data.get_icurve()
    ecurve = ElutioCurvProxy(xr_icurve)
    flimit = FlangeLimit(xr_data.M, xr_data.E, ecurve, xr_data.qv)
    stop = flimit.get_limit()
    pre_rg = PreliminaryRg(xr_data.M, xr_data.E, ecurve, xr_data.qv, stop, ip_effect_info=ip_effect_info)
    start = pre_rg.get_guinier_start_index()
    if small_angle_limit == 'none':
        start = 0
    elif small_angle_limit == 'extended':
        extended = _extended_small_angle_start(xr_data)
        if extended is not None:
            start = extended
    if nguiniers is not None:
        gstop = int(round(pre_rg.sg.guinier_stop * nguiniers))
        stop = min(stop, gstop)
    if return_object:
        return UsableQrange(start, stop, xr_icurve, pre_rg)
    else:
        return start, stop