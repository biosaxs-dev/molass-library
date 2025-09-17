"""
    SEC.Models.SdmComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf
from molass.LowRank.ComponentCurve import ComponentCurve

class SdmColumn:
    """
    A class to represent an SDM column.
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

class SdmComponentCurve(ComponentCurve):
    """
    A class to represent an SDM component curve.
    """
    def __init__(self, x, column, rg, scale):
        """
        Initializes the SDM component curve.
        """
        N, T, me, mp, x0, tI, N0, poresize, timescale = column.get_params()
        self.x = x
        self.tI = tI
        self._x = x - tI
        rho = rg/poresize
        if rho > 1.0:
            rho = 1.0
        ni = N*(1 - rho)**me
        ti = T*(1 - rho)**mp
        t0 = x0 - tI
        self.params = (ni, ti, N0, t0, timescale)
        self.scale = scale
    
    def get_y(self, x=None):
        """
        """
        if x is None:
            _x = self._x
        else:
            _x = x - self.tI
        return self.scale * dispersive_monopore_pdf(_x, *self.params)

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