"""
    Mapping.MappingInfo.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""

class MappingInfo:
    def __init__(self, slope, intercept, xr_peaks, uv_peaks, xr_moment, uv_moment, xr_curve, uv_curve):
        """
        """
        self.slope = slope
        self.intercept = intercept
        self.xr_peaks = xr_peaks
        self.uv_peaks = uv_peaks
        self.xr_moment = xr_moment
        self.uv_moment = uv_moment
        self.xr_curve = xr_curve
        self.uv_curve = uv_curve

    def __repr__(self):
        return f"MappingInfo(slope=%.3g, intercept=%.3g, xr_peaks=..., uv_peaks=..., xr_moment=..., uv_moment=...)" % (self.slope, self.intercept)
    
    def __str__(self):
        return self.__repr__()

    def get_mapped_x(self, xr_x):
        return xr_x * self.slope + self.intercept

    def get_mapped_index(self, i, xr_x, uv_x):
        yi = xr_x[i] * self.slope + self.intercept
        return int(round(yi - uv_x[0]))

    def get_mapped_curve(self, x, icurve):
        from scipy.interpolate import UnivariateSpline
        from molass.DataObjects.Curve import Curve
        spline = UnivariateSpline(icurve.x, icurve.y, s=0, ext=3)
        x_ = x * self.slope + self.intercept
        y_ = spline(x_)
        return Curve(x, y_)

    def compute_ratio_curve(self, y1, y2, debug=False, **kwargs):
        if debug:
            from importlib import reload
            import molass.Mapping.RatioCurve
            reload(molass.Mapping.RatioCurve)
        from molass.Mapping.RatioCurve import compute_ratio_curve_impl
        return compute_ratio_curve_impl(self, y1, y2, **kwargs)