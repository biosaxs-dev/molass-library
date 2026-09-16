"""
    Mapping.MappingInfo.py
"""
import numpy as np
class MappingInfo:
    """
    Contains information about the mapping between XR and UV data.

    Attributes
    ----------
    slope : float
        The slope of the linear mapping from XR to UV in the form y = slope * x + intercept.
    intercept : float
        The intercept of the linear mapping from XR to UV in the form y = slope * x + intercept.
    xr_peaks : list of tuples
        List of (position, intensity) tuples for XR peaks.
    uv_peaks : list of tuples
        List of (position, intensity) tuples for UV peaks.
    xr_moment : float
        The moment of the XR data.
    uv_moment : float
        The moment of the UV data.
    xr_curve : Curve
        The XR curve object.
    uv_curve : Curve
        The UV curve object.
    """
    def __init__(self, slope, intercept, xr_peaks, uv_peaks, xr_moment, uv_moment, xr_curve, uv_curve):
        """
        Initializes the MappingInfo object with the given parameters.
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

    def plot_diagnostics(self, title=None):
        """
        Visualize the XR/UV peak matching behind this mapping: XR and UV curves
        with their detected peaks marked, plus an overlay (UV mapped onto the XR
        frame axis via this mapping) so a mismatched peak pairing -- e.g. XR's
        tallest peak matched to a minor UV shoulder instead of UV's actual
        dominant peak -- is visible in one call (see molass-library issue #267).

        Parameters
        ----------
        title : str, optional
            Figure-level title.

        Returns
        -------
        fig, axes : matplotlib Figure and (3,) array of Axes
        """
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(ncols=3, figsize=(15, 4))
        if title is not None:
            fig.suptitle(title)
        ax1, ax2, ax3 = axes

        xr_x, xr_y = self.xr_curve.x, self.xr_curve.y
        uv_x, uv_y = self.uv_curve.x, self.uv_curve.y

        ax1.set_title("XR curve")
        ax1.plot(xr_x, xr_y)
        ax1.plot(xr_x[self.xr_peaks], xr_y[self.xr_peaks], 'o', color='C1')
        for k, p in enumerate(self.xr_peaks):
            ax1.annotate(str(k), (xr_x[p], xr_y[p]))

        ax2.set_title("UV curve")
        ax2.plot(uv_x, uv_y)
        ax2.plot(uv_x[self.uv_peaks], uv_y[self.uv_peaks], 'o', color='C1')
        for k, p in enumerate(self.uv_peaks):
            ax2.annotate(str(k), (uv_x[p], uv_y[p]))

        ax3.set_title("Overlay (UV mapped to XR frame axis)")
        mapped_uv_x = (uv_x - self.intercept) / self.slope
        ax3n = ax3.twinx()
        ax3.plot(xr_x, xr_y, color='C0', label='XR')
        ax3.plot(xr_x[self.xr_peaks], xr_y[self.xr_peaks], 'o', color='C0')
        ax3n.plot(mapped_uv_x, uv_y, color='C1', alpha=0.7, label='UV (mapped)')
        mapped_uv_peak_x = (uv_x[self.uv_peaks] - self.intercept) / self.slope
        ax3n.plot(mapped_uv_peak_x, uv_y[self.uv_peaks], 'o', color='C1')
        for k, (mapped_uv_x_k, xr_x_k) in enumerate(zip(mapped_uv_peak_x, xr_x[self.xr_peaks])):
            ax3.annotate(f"xr{k}", (xr_x_k, xr_y[self.xr_peaks[k]]))
            ax3n.annotate(f"uv{k}", (mapped_uv_x_k, uv_y[self.uv_peaks[k]]))
        ax3.set_xlabel("XR frame")
        ax3.legend(loc='upper left')
        ax3n.legend(loc='upper right')

        fig.tight_layout()
        return fig, axes
    
    def __iter__(self):
        """Allow unpacking of MappingInfo to (slope, intercept)."""
        return iter((self.slope, self.intercept))

    def get_mapped_x(self, xr_x):
        """Map XR x-values to UV x-values using the linear mapping.

        Parameters
        ----------
        xr_x : float or array-like
            The x-values in the XR domain.

        Returns
        -------
        uv_x : float or array-like
            The corresponding x-values in the UV domain.
        """
        xr_x = np.asarray(xr_x)
        return xr_x * self.slope + self.intercept

    def get_mapped_index(self, i, xr_x, uv_x):
        """Get the index in the UV data corresponding to the given index in the XR data.

        Parameters
        ----------
        i : int
            The index in the XR data.
        xr_x : array-like
            The x-values in the XR domain.
        uv_x : array-like
            The x-values in the UV domain.

        Returns
        -------
        index : int
            The corresponding index in the UV data.
        """
        yi = xr_x[i] * self.slope + self.intercept
        return int(round(yi - uv_x[0]))

    def get_mapped_curve(self, xr_icurve, uv_icurve, inverse_range=False, debug=False):
        """
        Get the mapped curve from XR to UV domain.

        Parameters
        ----------
        xr_icurve : Curve
            The XR curve object.
        uv_icurve : Curve
            The UV curve object.
        inverse_range : bool, optional
            If True, map the range of uv_icurve back to xr_icurve, by default False.
        debug : bool, optional
            If True, print debug information, by default False.

        Returns
        -------
        mapped_curve : Curve
            The mapped curve in the UV domain.
        """
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
        Compute the ratio curve, which is the ratio of the UV absorbance to the XR intensity,
        based on the mapping information.

        Parameters
        ----------
        mp_curve : Curve, optional
            The mapping curve to use, by default None.
        data_threshold : float, optional
            The data threshold to apply, by default 0.05.
        debug : bool, optional
            If True, print debug information, by default False.
        Returns
        -------
        ratio_curve : RatioCurve
        """
        if debug:
            from importlib import reload
            import molass.Mapping.RatioCurve
            reload(molass.Mapping.RatioCurve)
        from molass.Mapping.RatioCurve import _compute_ratio_curve_impl
        return _compute_ratio_curve_impl(self, mp_curve=mp_curve, data_threshold=data_threshold, debug=debug)