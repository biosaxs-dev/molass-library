"""
    Trimming.TrimmingInfo.py
"""
from molass.DataObjects.Curve import Curve

def custom_slice_string(slice_):
    """
    Convert a slice object to a string representation.
    This function removes the third 'None' from the representation of the slice:
    e.g., slice(1, 2, None) -> "slice(1, 2)"
    """
    return str(slice_).replace(", None)", ")")

class TrimmingInfo:
    def __init__(self, xr_slices=None, uv_slices=None, mapping=None):
        self.xr_slices = xr_slices
        self.uv_slices = uv_slices
        self.mapping = mapping

    def copy(self, xr_slices=None, uv_slices=None, mapping=None):
        """
        Returns a new TrimmingInfo object with specified xr_slices, uv_slices, and mapping.
        If any of the parameters are None, it uses the current object's attributes.
        """
        if xr_slices is None:
            xr_slices = self.xr_slices
        if uv_slices is None:
            uv_slices = self.uv_slices
        if mapping is None:
            mapping = self.mapping
        return TrimmingInfo(xr_slices=xr_slices, uv_slices=uv_slices, mapping=mapping)

    def get_trimmed_mapping(self, xr_slices=None, uv_slices=None):
        """
        Returns a new MappingInfo object with xr_slices and uv_slices applied.
        This is a temporary fix for plot_compact. Removing attributes xr_peaks, uv_peaks, xr_moment, uv_moment,
        and xr_curve, uv_curve should be considered.
        """
        from copy import deepcopy
        
        ret_mapping = deepcopy(self.mapping)
        
        if xr_slices is None:
            xr_slices = self.xr_slices
        if uv_slices is None:
            uv_slices = self.uv_slices

        xr_jslice = xr_slices[1]
        uv_jslice = uv_slices[1]
        if xr_jslice is not None:
            ret_mapping.xr_peaks = None
            ret_mapping.xr_moment = None
            xr_curve = ret_mapping.xr_curve
            ret_mapping.xr_curve = Curve(
                x=xr_curve.x[xr_jslice],
                y=xr_curve.y[xr_jslice],
                type=xr_curve.type
                )

        if uv_jslice is not None:
            ret_mapping.uv_peaks = None
            ret_mapping.uv_moment = None
            uv_curve = ret_mapping.uv_curve
            ret_mapping.uv_curve = Curve(
                x=uv_curve.x[uv_jslice],
                y=uv_curve.y[uv_jslice],
                type=uv_curve.type
                )

        return ret_mapping

    def __repr__(self):
        return "TrimmingInfo(xr_slices=%s, uv_slices=%s, mapping=%s)" % (
            custom_slice_string(self.xr_slices), custom_slice_string(self.uv_slices), self.mapping)
    
    def __str__(self):
        return self.__repr__()