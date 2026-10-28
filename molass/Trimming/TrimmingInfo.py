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
    """
    Holds information about trimming of XR and UV data, as well as the associated mapping.

    Attributes
    ----------
    xr_slices : tuple of slices or None
        The slices applied to the XR data (spectral axis, temporal axis).
    uv_slices : tuple of slices or None
        The slices applied to the UV data (spectral axis, temporal axis).
    mapping : MappingInfo or None
        The mapping information between XR and UV data.
    small_angle_limit : str or None
        How the start of the angular range (the lowest q kept) was determined:
        ``'extended'``, ``'guinier'``, ``'none'`` or ``'explicit'`` (given as ``xr_qr``);
        None if unknown (e.g. trimming by ``jranges``).
    """
    def __init__(self, xr_slices=None, uv_slices=None, mapping=None, legacy_info=None, small_angle_limit=None):
        """
        Initializes the TrimmingInfo object with the given parameters.
        
        Parameters
        ----------
        xr_slices : tuple of slices or None, optional
            The slices applied to the XR data (spectral axis, temporal axis).
            If None, no trimming is applied to the XR data.
        uv_slices : tuple of slices or None, optional
            The slices applied to the UV data (spectral axis, temporal axis).
            If None, no trimming is applied to the UV data.
        mapping : MappingInfo or None, optional
            The mapping information between XR and UV data.
            If None, no mapping information is associated.
        small_angle_limit : str or None, optional
            How the start of the angular range was determined (see the class docstring).
        """
        self.xr_slices = xr_slices
        self.uv_slices = uv_slices
        self.mapping = mapping
        self.legacy_info = legacy_info
        self.small_angle_limit = small_angle_limit

    def copy(self, xr_slices=None, uv_slices=None, mapping=None, legacy_info=None, small_angle_limit=None):
        """
        Returns a new TrimmingInfo object with specified xr_slices, uv_slices, and mapping.
        If any of the parameters are None, it uses the current object's attributes.
        """
        if xr_slices is None:
            xr_slices = self.xr_slices
        elif small_angle_limit is None and (self.xr_slices is None or xr_slices[0] != self.xr_slices[0]):
            # the angular slice was replaced: it is no longer the one the policy produced
            small_angle_limit = 'explicit'
        if uv_slices is None:
            uv_slices = self.uv_slices
        if mapping is None:
            mapping = self.mapping
        if legacy_info is None:
            legacy_info = self.legacy_info
        if small_angle_limit is None:
            small_angle_limit = self.small_angle_limit
        return TrimmingInfo(xr_slices=xr_slices, uv_slices=uv_slices, mapping=mapping, legacy_info=legacy_info,
                            small_angle_limit=small_angle_limit)

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
        text = "TrimmingInfo(xr_slices=%s, uv_slices=%s, mapping=%s" % (
            custom_slice_string(self.xr_slices), custom_slice_string(self.uv_slices), self.mapping)
        if self.small_angle_limit is not None:
            text += ", small_angle_limit=%r" % self.small_angle_limit
        return text + ")"
    
    def __str__(self):
        return self.__repr__()
    
    def update_legacy_settings(self):
        """Export the TrimmingInfo to legacy settings."""
        from molass_legacy._MOLASS.SerialSettings import set_setting
        assert self.legacy_info is not None, "No legacy_info available to update legacy settings."
        set_setting('xr_restrict_list', self.legacy_info['xr_restrict_list'])
        set_setting('uv_restrict_list', self.legacy_info['uv_restrict_list'])