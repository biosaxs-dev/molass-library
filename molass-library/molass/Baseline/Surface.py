"""
    Baseline.Surface.py
"""
import numpy as np

class Surface:
    """A class to represent a 2D surface defined by the outer product of two 1D arrays.

    Attributes
    ----------
    Z : 2D array-like
        The 2D surface defined by the outer product of the two input arrays.
    spline : RectBivariateSpline or None
        A spline representation of the surface. If None, no spline is available.
    """
    def __init__(self, x, y, add_spline=False):
        """ Initializes the Surface object with the given x and y arrays.
        Parameters
        ----------
        x : array-like
            The x-values defining the surface.
        y : array-like
            The y-values defining the surface.
        add_spline : bool, optional
            Whether to create a spline representation of the surface (default is False).
        """
        self.Z = x[:,np.newaxis] @ y[np.newaxis,:]
        if add_spline:
            from scipy.interpolate import RectBivariateSpline
            self.spline = RectBivariateSpline(x, y, self.Z)
        else:
            self.spline = None

    def get(self):
        """Get the 2D surface array.

        Returns
        -------
        Z : 2D array-like
            The 2D surface defined by the outer product of the two input arrays.
        """
        return self.Z

    def __call__(self, x, y):
        """Evaluate the surface at the given (x, y) coordinates using the spline.
        Parameters
        ----------
        x : float or array-like
            The x-coordinates where the surface is evaluated.
        y : float or array-like
            The y-coordinates where the surface is evaluated.
        Returns
        -------
        Z : float or array-like
            The evaluated surface values at the given (x, y) coordinates.
        """
        assert self.spline is not None
        return self.spline(x, y)