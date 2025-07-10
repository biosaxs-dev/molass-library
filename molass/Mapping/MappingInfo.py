"""
    Mapping.MappingInfo.py
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
        xr_x = np.asarray(xr_x)
        return xr_x * self.slope + self.intercept

    def get_mapped_index(self, i, xr_x, uv_x):
        yi = xr_x[i] * self.slope + self.intercept
        return int(round(yi - uv_x[0]))

    def get_mapped_curve(self, xr_icurve, uv_icurve, inverse_range=False, debug=False):
        from molass.DataObjects.Curve import Curve
        spline = uv_icurve.get_spline()
    
        if inverse_range:
            def inverse_x(z):
                return int(round((z - self.intercept) / self.slope))
            
            mapped_ends = []
            for end_uv_x in uv_icurve.x[[0,-1]]:
                end_xr_x = inverse_x(end_uv_x)
                mapped_ends.append(end_xr_x)
            mapped_ends = np.array(mapped_ends)

            if debug:   
                import matplotlib.pyplot as plt
                x_ = xr_icurve.x * self.slope + self.intercept
                fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
                ax1.plot(uv_icurve.x, uv_icurve.y, label='uv_icurve')
                ax1.plot(x_, spline(x_), ':', label='mapped range')
                ax1.legend()
                ax2.plot(xr_icurve.x, xr_icurve.y, label='xr_icurve')
                for mapped_x in mapped_ends:
                    ax2.axvline(mapped_x, color='gray', linestyle='--', label=f'uv_icurve x={mapped_x}')
                ax2.legend()
                fig.tight_layout()
                plt.show()

            cx = np.arange(mapped_ends[0], mapped_ends[1] + 1)
        else:
            cx = xr_icurve.x

        x_ = cx * self.slope + self.intercept
        cy = spline(x_)
        return Curve(cx, cy)

    def compute_ratio_curve(self, mp_curve=None, data_threshold=0.05, debug=False):
        """
        Compute the ratio curve based on the mapping information.
        """
        if debug:
            from importlib import reload
            import molass.Mapping.RatioCurve
            reload(molass.Mapping.RatioCurve)
        from molass.Mapping.RatioCurve import compute_ratio_curve_impl
        return compute_ratio_curve_impl(self, mp_curve=mp_curve, data_threshold=data_threshold, debug=debug)