"""
    LowRank.RankEstimator.py

    This module contains functions used to estimate the rank.
"""

RANK2_SCD_LIMIT = 5.0
class EcurveProxyCds:
    """
    A proxy class for Ecurve used in ConcDepend.
    Originally from molass_legacy.Baseline.LpmInspect.
    """
    def __init__(self, decomposition, j_slice):
        e_curve = decomposition.xr_icurve
        self.e_curve = e_curve
        self.x = e_curve.x
        self.y = e_curve.y
        self.max_y = e_curve.max_y
        self.spline = e_curve.get_spline()
        self.j_slice = j_slice
        paired_ranges = decomposition.get_pairedranges()
        peak_info = []
        for pr in paired_ranges:
            if len(pr.ranges) == 1:
                range_ = pr.ranges[0]
                middle = (range_[0] + range_[1]) // 2
                peak_info.append((range_[0], middle, range_[1]))
            else:
                peak_info.append([*pr.ranges[0], pr.ranges[1][1]])
        self.peak_info = peak_info

def compute_scds_impl(decomposition, **kwargs):
    """
    Compute the SCDs (Score of Concentration Dependence) for a given decomposition.

    Task: Verify the precision of the SCDs.
    """
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.Backward.RgDiffRatios
        reload(molass.Backward.RgDiffRatios)
    from molass.Backward.RgDiffRatios import RgDiffRatios
    from molass_legacy.Conc.ConcDepend import ConcDepend
    ecurve_for_cds = EcurveProxyCds(decomposition, slice(None, None))   # jslice

    xr = decomposition.ssd.xr
    cd = ConcDepend(xr.qv, xr.M, xr.E, ecurve_for_cds)
    rdr = RgDiffRatios(decomposition)
    rdr_hints = rdr.get_rank_hints()
    cds_list = cd.compute_judge_info(rdr_hints)
    if debug:
        print(f"cds_list: {cds_list}")
    scds = [pair[1] for pair in cds_list]
    return scds

def scd_to_rank(scd):
    """
    Convert a single SCD value to a rank.
    """
    rank = 1 if scd < RANK2_SCD_LIMIT else 2
    return rank