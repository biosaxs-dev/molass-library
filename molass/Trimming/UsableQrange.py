"""
    Trimming.UsableQrange.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
class UsableQrange:
    def __init__(self, start, stop, icurve, pre_rg):
        self.start = start
        self.stop = stop
        self.icurve = icurve
        self.pre_rg = pre_rg

def get_usable_qrange_impl(xr_data, ip_effect_info=False, nguiniers=None, return_object=False, debug=True):
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