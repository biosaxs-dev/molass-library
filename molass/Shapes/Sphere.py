"""
Shapes.Sphere.py
"""

import numpy as np

class Sphere:
    """
    Sphere class to represent a spherical density space.
    """
    def __init__(self, radius, center=None):
        self.radius = radius
        self.center = center

    def get_condition(self, xx, yy, zz, center=None):
        """
        Get the condition for the sphere.
        """
        if center is None:
            center = self.center
            if center is None:
                assert xx.shape == yy.shape and yy.shape == zz.shape, "xx, yy, zz must have the same shape."
                center = np.array(xx.shape)/2
        return (xx - center[0])**2 + (yy - center[1])**2 + (zz - center[2])**2 <= self.radius**2

    def get_rg(self):
        """
        Calculate the radius of gyration of the sphere.

        Returns
        -------
        float
            The radius of gyration of the sphere.
        """
        return self.radius * np.sqrt(5/3)

    def get_volume(self):
        """
        Calculate the volume of the sphere.

        Returns
        -------
        float
            The volume of the sphere.
        """
        return (4/3) * np.pi * self.radius**3
