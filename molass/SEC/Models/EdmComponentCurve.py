"""
    SEC.Models.EdmComponentCurve.py

"""
import numpy as np
from molass_legacy.Models.RateTheory.EDM import edm_impl
from molass.LowRank.ComponentCurve import ComponentCurve

class EdmColumn:
    """
    A class to represent an EDM column.

    Attributes
    ----------
    params : tuple
        The parameters of the EDM column (N, T, me, mp, x0, tI, N0, poresize, timescale).
    """
    def __init__(self, params):
        """
        Initializes the EDM column.

        Parameters
        ----------
        params : tuple
            The column parameters (N, T, me, mp, x0, tI, N0, poresize, timescale).
        """
        self.params = params

    def get_params(self):
        """
        Returns the parameters of the EDM column.

        Returns
        -------
        tuple
            The parameters of the EDM column.
        """
        return self.params

class EdmComponentCurve(ComponentCurve):
    """
    A class to represent an EDM component curve.

    Attributes
    ----------
    x : array-like
        The x values.
    params : tuple
        The parameters of the EDM column (N, T, me, mp, x0,
    """
    def __init__(self, x, params):
        """
        Initializes the EDM component curve.
        Parameters
        ----------
        x : array-like
            The x values.
        params : tuple
            The column parameters (N, T, me, mp, x0, tI, N0, poresize, timescale).
        """
        self.x = x
        self.params = params
    
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

        """
        if x is None:
            x = self.x
        return edm_impl(x, *self.params)

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
            If the peak top x calculation is not implemented for the current model.
        """
        raise NotImplementedError("Peak top x calculation is not implemented for SDM model.")