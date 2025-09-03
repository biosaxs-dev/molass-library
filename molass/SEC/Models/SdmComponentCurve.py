"""
    SEC.Models.SdmComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf
from molass.LowRank.ComponentCurve import ComponentCurve

class SdmComponentCurve(ComponentCurve):
    """
    A class to represent an SDM component curve.
    """
    def __init__(self, x, params):
        super().__init__(x, params)
    
    def get_xy(self):
        """
        """
        x = self.x
        return x, dispersive_monopore_pdf(x, *self.params)
    
    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.
        """
        raise NotImplementedError("Peak top x calculation is not implemented for SDM model.")