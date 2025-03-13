"""
    Trimming.TrimmingInfo.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""

class TrimmingInfo:
    def __init__(self, xr_slices=None, uv_slices=None, mapping=None):
        self.xr_slices = xr_slices
        self.uv_slices = uv_slices
        self.mapping = mapping
    
    def __repr__(self):
        return f"TrimmingInfo(xr_slices={self.xr_slices}, uv_slices={self.uv_slices}, mapping={self.mapping})"
    
    def __str__(self):
        return self.__repr__()