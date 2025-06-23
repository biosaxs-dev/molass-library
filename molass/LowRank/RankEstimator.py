"""
    LowRank.RankEstimator.py

    This module contains functions used to estimate the rank.
"""

def estimate_component_ranks_using_scd(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs):

    num_components = len(xr_ccurves)
    ranks = [1] * num_components  # Default rank for each component is 1
    return ranks