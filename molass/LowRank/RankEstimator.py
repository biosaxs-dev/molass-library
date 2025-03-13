"""
    LowRank.RankEstimator.py

    This module contains functions used to estimate the rank.

    Copyright (c) 2025, SAXS Team, KEK-PF
"""

def estimate_rank(ssd):
    xr_icurve = ssd.xr.get_icurve()
    xr_peaks = xr_icurve.get_peaks()
    return len(xr_peaks)