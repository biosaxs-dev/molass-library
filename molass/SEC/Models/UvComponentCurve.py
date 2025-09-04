"""
    SEC.Models.UvComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf
from molass.LowRank.ComponentCurve import ComponentCurve

class UvComponentCurve(ComponentCurve):
    """
    A class to represent a UV component curve.
    """
    def __init__(self, x, mapping, xr_ccurve, scale):
        """
        Initializes the UV component curve.
        x: x values
        mapping: mapping from XR to UV
        xr_ccurve: corresponding XR component curve
        scale: scaling factor
        """
        self.x = x
        self.mapping = mapping
        self.xr_ccurve = xr_ccurve
        self.scale = scale

    def get_y(self, x=None):
        """
        """
        if x is None:
            x = self.x
        x_ = self.mapping.inv(x)
        return self.scale * self.xr_ccurve.get_y(x_)  # scale * corresponding XR curve y values

    def get_xy(self):
        """
        """
        x = self.x
        return x, self.get_y()
    
    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.
        """
        raise NotImplementedError("Peak top x calculation is not implemented for SDM model.")