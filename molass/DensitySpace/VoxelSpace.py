"""
DensitySpace.VoxelSpace.py
"""

import numpy as np
import matplotlib.pyplot as plt

def get_meshgrid(N):
    """
    Create a meshgrid for the electron density space.

    Returns
    -------
    tuple
        A tuple containing the meshgrid arrays (x, y, z).
    """
    x = y = z = np.arange(N)
    return np.meshgrid(x, y, z)

class VoxelSpace:
    """
    VoxelSpace class to handle voxel-based density spaces.
    """
    def __init__(self, N, shape):
        self.rho = np.zeros((N, N, N))

        xx, yy, zz = get_meshgrid(N)
        shape_condition = shape.get_condition(xx, yy, zz)
        self.rho[shape_condition] = 1

    def plot_as_dots(self, ax=None):
        """
        Plot the voxel space.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to plot on.
        """
        from learnsaxs import draw_voxles_as_dots
        if ax is None:
            fig, ax = plt.subplots(subplot_kw={'projection': '3d'})

        draw_voxles_as_dots(ax, self.rho)