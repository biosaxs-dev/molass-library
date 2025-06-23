"""
    LowRank.RankEstimator.py

    This module contains functions used to estimate the rank.
"""

def legacy_reference():
    from molass_legacy.Conc.ConcDepend import ConcDepend
    from molass_legacy.Baseline.LpmInspect_for_paper import EcurveProxyCds
    ecurve_for_cds = EcurveProxyCds(xr.e_curve, j_slice)
    cd = ConcDepend(q, data, error, ecurve_for_cds)
    cds_list = cd.compute_judge_info()
    cds0 = cds_list[peakno][1]

def compute_scds_impl(xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs):
    """
    See above.
    """

    num_components = len(xr_ccurves)
    scds = [1] * num_components  # Default rank for each component is 1
    return scds

def scd_to_rank(scd):
    """
    Convert a single SCD value to a rank.
    """
    return 1