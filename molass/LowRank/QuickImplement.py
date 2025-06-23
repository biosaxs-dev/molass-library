"""
LowRank.QuickImplement
"""
from importlib import reload

def make_lowrank_info_impl(ssd, num_components=None, ranks=None, **kwargs):    
    debug = kwargs.get('debug', False)
    if debug:
        import molass.LowRank.CoupledAdjuster
        reload(molass.LowRank.CoupledAdjuster)
    from molass.LowRank.CoupledAdjuster import make_component_curves

    xr_icurve, xr_ccurves, uv_icurve, uv_ccurves = make_component_curves(ssd, num_components, **kwargs)

    if num_components is None:
        num_components = len(xr_ccurves)

    if ranks is None:
        use_scd = kwargs.get('use_scd', False)
        if use_scd:
            if debug:
                import molass.LowRank.RankEstimator
                reload(molass.LowRank.RankEstimator)
            from molass.LowRank.RankEstimator import estimate_component_ranks_using_scd
            ranks = estimate_component_ranks_using_scd(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs)
        else:
            ranks = [1] * num_components  # Default rank for each component is 1
    else:
        if num_components != len(ranks):
            from molass.Except.ExceptionTypes import InconsistentUseError
            raise InconsistentUseError("The number of components and ranks should be the same.")

    if debug:
        import molass.LowRank.LowRankInfo
        reload(molass.LowRank.LowRankInfo)
    from molass.LowRank.LowRankInfo import LowRankInfo

    return LowRankInfo(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, ranks, **kwargs) 