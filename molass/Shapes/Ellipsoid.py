"""
Shapes.Ellipsoid.py
"""

import numpy as np

class Ellipsoid:
    """
    Sphere class to represent a spherical density space.

    Attributes
    ----------
    a : float
        The semi-axis length along the x-axis.
    b : float
        The semi-axis length along the y-axis.
    c : float
        The semi-axis length along the z-axis.
    center : tuple of float, optional
        The center of the ellipsoid. If None, the center is assumed to be at the
        center of the grid when used in get_condition.
    """
    def __init__(self, a, b, c, center=None):
        """
        Initialize the Ellipsoid object.
        Parameters
        ----------
        a : float
            The semi-axis length along the x-axis.
        b : float
            The semi-axis length along the y-axis.
        c : float
            The semi-axis length along the z-axis.
        center : tuple of float, optional
            The center of the ellipsoid. If None, the center is assumed to be at the
            center of the grid when used in get_condition.
        """
        self.a = a
        self.b = b
        self.c = c
        self.center = center

    def get_condition(self, xx, yy, zz, center=None):
        """
        Get the condition for the ellipsoid.

        Parameters
        ----------
        xx : np.ndarray
            The x-coordinates grid.
        yy : np.ndarray
            The y-coordinates grid.
        zz : np.ndarray
            The z-coordinates grid.
        center : tuple of float, optional
            The center of the ellipsoid. If None, the center attribute of the object is used.
            If the center attribute is also None, the center is assumed to be at the center of the grid.
            
        Returns
        -------
        np.ndarray
            A boolean array where True indicates points inside the ellipsoid.
        """
        if center is None:
            center = self.center
            if center is None:
                assert xx.shape == yy.shape and yy.shape == zz.shape, "xx, yy, zz must have the same shape."
                center = np.array(xx.shape)/2
        return ((xx - center[0])**2 / self.a**2 + (yy - center[1])**2 / self.b**2 + (zz - center[2])**2 / self.c**2) <= 1

    def get_rg(self):
        """
        Calculate the radius of gyration of the ellipsoid.

        Returns
        -------
        float
            The radius of gyration of the ellipsoid.
        """
        return np.sqrt((self.a**2 + self.b**2 + self.c**2) / 5)

    def get_volume(self):
        """
        Calculate the volume of the ellipsoid.

        Returns
        -------
        float
            The volume of the ellipsoid.
        """
        return (4/3) * np.pi * self.a * self.b * self.c
