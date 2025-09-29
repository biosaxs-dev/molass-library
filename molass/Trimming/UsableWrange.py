"""
    Trimming.UsableWrange.py
"""
from bisect import bisect_right

def get_usable_wrange_impl(ssd):
    """
    Get the usable W range for the given SSD data.

    Parameters
    ----------
    ssd : SSDData
        The SSD data to analyze.

    Returns
    -------
    UsableWrange or (int, int)
        The usable W range as a UsableWrange object or as (start, stop) tuple.
    """
    i = bisect_right(ssd.wv, 250)
    j = None
    return i, j