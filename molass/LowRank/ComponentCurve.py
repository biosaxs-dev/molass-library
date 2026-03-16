"""
    LowRank.ComponentCurve.py
"""
import numpy as np
from molass.SEC.Models.Simple import egh

class ComponentCurve:
    """
    A class to represent a component curve.

    This object stores the *elution-curve* EGH parameters (H, tR, sigma, tau)
    and can evaluate the model curve, but it does **not** hold scattering
    profiles and therefore cannot compute Rg directly.

    To obtain Rg values, use one of:

    - ``decomp.get_rgs()`` — list of Rg for all components.
    - ``decomp.get_xr_components()`` — returns ``XrComponent`` objects,
      each of which has ``get_guinier_object()`` for full Guinier-fit results.

    Attributes
    ----------
    x : array-like
        The x-values of the component curve.
    params : array-like
        The EGH parameters ``[H, tR, sigma, tau]`` of the component curve.
    moment : Moment or None
        The moment of the component curve. Computed on demand. If None, it has not been computed yet.
    """
    def __init__(self, x, params):
        """ Initializes the ComponentCurve object with the given x-values and parameters.

        Parameters
        ----------
        x : array-like
            The x-values of the component curve.
        params : array-like
            The parameters of the component curve.
        """
        self.x = x
        self.params = np.asarray(params)
        self.moment = None
        self.model = 'egh'  # default model

    @property
    def y(self):
        """The y-values of the component curve evaluated at self.x."""
        return self.get_y(self.x)

    def get_y(self, x=None):
        """
        Returns the y-values of the component curve.

        Parameters
        ----------
        x : array-like or None, optional
            The x-values to compute the y-values for. If None, uses the object's x-values.

        Returns
        -------
        array-like
            The y-values of the component curve.    
        """
        if x is None:
            x = self.x  
        return egh(x, *self.params)

    def get_xy(self):
        """
        Returns the x and y values of the component curve.

        Returns
        -------
        tuple of array-like
            The x and y values of the component curve.
        """
        x = self.x
        return x, self.get_y()

    def get_moment(self):
        """
        Returns the moment of the component curve.

        Returns
        -------
        Moment
            The moment of the component curve.
        """
        if self.moment is None:
            from molass.Stats.Moment import Moment
            x, y = self.get_xy()
            self.moment = Moment(x, y)
        return self.moment

    def get_params(self):
        """
        Returns the parameters of the component curve.

        Returns
        -------
        array-like
            The parameters of the component curve.
        """
        return self.params

    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.
        
        Returns
        -------
        float
            The x value at the peak top.
        """
        return self.params[1]   # peak position in EGH model, note that this in valid only for EGH model
    
    def get_scale_param(self):
        """
        Returns the scale parameter.

        Returns
        -------
        float
            The scale parameter.
        """
        return self.params[0]   # scale in EGH model