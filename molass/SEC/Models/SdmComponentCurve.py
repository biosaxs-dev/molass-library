"""
    SEC.Models.SdmComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.Stochastic.DispersivePdf import dispersive_monopore_pdf
from molass.LowRank.ComponentCurve import ComponentCurve

class SdmColumn:
    """
    A class to represent an SDM column.

    Attributes
    ----------
    params : tuple
        The parameters of the SDM column (N, T, me, mp, x0, tI, N0, poresize, timescale)
    """
    def __init__(self, params):
        """
        Initializes the SDM column.

        Parameters
        ----------
        params : tuple
            The column parameters (N, T, me, mp, x0, tI, N0, poresize, timescale)
        """
        self.params = params

    def get_params(self):
        """
        Returns the parameters of the SDM column.

        Returns
        -------
        tuple
            The parameters of the SDM column.
        """
        return self.params

class SdmComponentCurve(ComponentCurve):
    """
    A class to represent an SDM component curve.

    Attributes
    ----------
    x : array-like
        The x values.
    params : tuple
        The parameters of the SDM column (N, T, me, mp, x0, tI, N0, poresize, timescale).
    """
    def __init__(self, x, column, rg, scale):
        """
        Initializes the SDM component curve.

        Parameters
        ----------
        x : array-like
            The x values.
        column : SdmColumn
            The SDM column object containing the parameters.
        rg : float
            The radius of gyration for this component.
        scale : float
            The scaling factor.
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
            _x = self._x
        else:
            _x = x - self.tI
        return self.scale * dispersive_monopore_pdf(_x, *self.params)

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

        Raises
        ------
        NotImplementedError
            Peak top x calculation is not implemented for SDM model.
        """
        raise NotImplementedError("Peak top x calculation is not implemented for SDM model.")