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

def get_usable_qrange_impl(xr_data, ip_effect_info=False, nguiniers=None, return_object=False, debug=True):
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
        
    Returns
    -------
    UsableQrange or (int, int)
        The usable Q range as a UsableQrange object or as (start, stop) tuple.
    """
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
    if nguiniers is not None:
        gstop = int(round(pre_rg.sg.guinier_stop * nguiniers))
        stop = min(stop, gstop)
    if return_object:
        return UsableQrange(start, stop, xr_icurve, pre_rg)
    else:
        return start, stop