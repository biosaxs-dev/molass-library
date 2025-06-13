"""
    Mapping.MappingInfo.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
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

    def get_mapped_curve(self, xr_icurve, uv_icurve, extend_x=False):
        from molass.DataObjects.Curve import Curve
        spline = uv_icurve.get_spline()
        x_ = xr_icurve.x * self.slope + self.intercept
        cx = xr_icurve.x
        if extend_x:
            def inverse_x(z):
                return int(round((z - self.intercept) / self.slope))    
            # extend the curve to cover the full range of uv_icurve.x
            cx_list = []
            if uv_icurve.x[0] < x_[0]:
                x_start = inverse_x(uv_icurve.x[0])
                cx_list.append(np.arange(x_start, x_[0]))
            if uv_icurve.x[-1] > x_[-1]:
                x_end = inverse_x(uv_icurve.x[-1])
                cx_list.append(np.arange(x_[0], x_end + 1))
            if len(cx_list) > 0:
                ex = np.concatenate(cx_list)
                print(f"Extended x range: {ex[0]} to {ex[-1]}")
                x_ = ex * self.slope + self.intercept
                cx = ex
            else:
                # no extension needed
                # and no change to x_, cx
                pass

        cy = spline(x_)
        return Curve(cx, cy)

    def compute_ratio_curve(self, y1, y2, debug=False, **kwargs):
        if debug:
            from importlib import reload
            import molass.Mapping.RatioCurve
            reload(molass.Mapping.RatioCurve)
        from molass.Mapping.RatioCurve import compute_ratio_curve_impl
        return compute_ratio_curve_impl(self, y1, y2, **kwargs)