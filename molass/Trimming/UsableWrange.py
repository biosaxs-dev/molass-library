"""
    Trimming.UsableWrange.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
from bisect import bisect_right

def get_usable_wrange_impl(ssd):
    i = bisect_right(ssd.wv, 250)
    j = None
    return i, j