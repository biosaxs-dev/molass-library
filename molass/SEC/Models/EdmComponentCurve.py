"""
    SEC.Models.EdmComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.RateTheory.EDM import edm_impl
from molass.LowRank.ComponentCurve import ComponentCurve

class EdmColumn:
    """
    A class to represent an EDM column.
    """
    def __init__(self, params):
        """
        params: (N, T, me, mp, x0, tI, N0, poresize, timescale)
        """
        self.params = params

    def get_params(self):
        """
        Returns the parameters of the SDM column.
        """
        return self.params

class EdmComponentCurve(ComponentCurve):
    """
    A class to represent an EDM component curve.
    """
    def __init__(self, x, params):
        """
        Initializes the EDM component curve.
        """
        self.x = x
        self.params = params
    
    def get_y(self, x=None):
        """
        """
        if x is None:
            x = self.x
        return edm_impl(x, *self.params)

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