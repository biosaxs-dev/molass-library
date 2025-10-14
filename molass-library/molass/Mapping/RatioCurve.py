"""
    Mapping.RatioCurve.py
"""
import numpy as np
from molass.DataObjects.Curve import Curve

class RatioCurve(Curve):
    """
    Represents the ratio curve between mapped UV data and XR data.

    Attributes
    ----------
    x : array-like
        The x-values of the ratio curve.
    y : array-like
        The y-values of the ratio curve, representing the ratio of mapped UV intensity to XR intensity.
    """
    def __init__(self, x, y, type="i"):
        """
        Initializes the RatioCurve with given x and y values.

        Parameters
        ----------
        x : array-like
            The x-values of the ratio curve.
        y : array-like
            The y-values of the ratio curve.
        type : str, optional
            The type of the ratio curve (default is "i").
        """
        super().__init__(x, y, type=type)

def _compute_ratio_curve_impl(mapping, mp_curve=None, data_threshold=0.05, debug=False):
    if debug:
        import molass.DataUtils.Outliers
        from importlib import reload
        reload(molass.DataUtils.Outliers)
    from molass.DataUtils.Outliers import remove_outliers
    xr_curve = mapping.xr_curve
    if mp_curve is None:
        uv_curve = mapping.uv_curve
        mp_curve = mapping.get_mapped_curve(xr_curve, uv_curve, inverse_range=True, debug=debug)

    spline = xr_curve.get_spline()
    xr_y = spline(mp_curve.x)
    ratio = remove_outliers(mp_curve.y / xr_y, repeat=2)
    uv_valid = np.abs(mp_curve.y) > mp_curve.get_max_y()*data_threshold
    xr_valid = np.abs(xr_y) > xr_curve.get_max_y()*data_threshold
    valid = np.logical_and(uv_valid, xr_valid)
    if not np.any(valid):
        raise ValueError("No valid data points found for ratio calculation.")
    ratio[~valid] = np.nan  # Set invalid points to NaN
    return RatioCurve(mp_curve.x, ratio)