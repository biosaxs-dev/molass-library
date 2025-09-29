"""
    SEC.Models.UvComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf
from molass.LowRank.ComponentCurve import ComponentCurve

class UvComponentCurve(ComponentCurve):
    """
    A class to represent a UV component curve.

    Attributes
    ----------
    x : array-like
        The x values.
    mapping : Mapping
        The mapping from XR to UV.
    xr_ccurve : ComponentCurve
        The corresponding XR component curve.
    scale : float
        The scaling factor.
    """
    def __init__(self, x, mapping, xr_ccurve, scale):
        """
        Initializes the UV component curve.

        Parameters
        ----------
        x : array-like
            The x values.
        mapping : Mapping
            The mapping from XR to UV.
        xr_ccurve : ComponentCurve
            The corresponding XR component curve.
        scale : float
            The scaling factor. 
        """
        self.x = x
        self.mapping = mapping
        self.xr_ccurve = xr_ccurve
        self.scale = scale

    def get_y(self, x=None):
        """
        Returns the y values for the given x values.

        Parameters
        ----------
        x : array-like or None, optional
            The x values to get the y values for. If None, uses the object's x values.

        Returns
        -------
        array-like
            The y values corresponding to the given x values.
        """
        if x is None:
            x = self.x
        x_ = self.mapping.inv(x)
        return self.scale * self.xr_ccurve.get_y(x_)  # scale * corresponding XR curve y values

    def get_xy(self):
        """
        Returns the x and y values as a tuple.

        Returns
        -------
        tuple
            A tuple containing the x values and the corresponding y values.
        """
        x = self.x
        return x, self.get_y()
    
    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.

        Returns
        -------
        float
            The x value at the peak top.
        """
        raise NotImplementedError("Peak top x calculation is not implemented for SDM model.")