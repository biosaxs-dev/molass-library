"""
# This module contains the SAXS simulator class.

"""
import numpy as np
import matplotlib.pyplot as plt
from learnsaxs import draw_voxles_as_dots, draw_detector_image
from .DetectorInfo import get_detector_info
from .DenssLike import get_detector_info_from_density

class SaxsInfo:
    """
    Class to represent the SAXS information.
    """
    def __init__(self, electron_density, ft_image, detector_info):
        """
        Initialize the SAXS information.

        Parameters
        ----------
        electron_density : np.ndarray
            The electron density information.
        ft_image : np.ndarray
            The Fourier transform image.
        detector_info : np.ndarray
            The detector information.
        """
        self.electron_density = electron_density
        self.ft_image = ft_image
        self.detector_info = detector_info

class ElectronDensitySpace:
    """
    Class to represent the electron density space.
    """
    def __init__(self, N=32):
        """
        Initialize the electron density space.

        Parameters
        ----------
        N : int, optional
            The size of the grid (default is 32).
        """
        self.N = N

    def get_meshgrid(self):
        """
        Create a meshgrid for the electron density space.

        Returns
        -------
        tuple
            A tuple containing the meshgrid arrays (x, y, z).
        """
        x = y = z = np.arange(self.N)
        return np.meshgrid(x, y, z)

    def compute_saxs(self, shape_condition, q=None, use_denss=False):
        """
        Compute the SAXS pattern for a given shape condition.

        Parameters
        ----------
        shape_condition : np.ndarray
            A boolean array representing the shape to be computed.
        
        q : np.ndarray, optional
            The q values for the SAXS pattern (default is None, which generates a default range).    

        Returns
        -------
        np.ndarray
            The computed SAXS pattern.
        """
        N = self.N
        space = np.zeros((N,N,N))
        space[shape_condition] = 1

        if q is None:
            q = np.linspace(0.005, 0.5, 100)
 
        if use_denss:
            ft_image = None
            info = get_detector_info_from_density(q, space)
        else:
            F = np.fft.fftn(space)
            ft_image = np.abs(F)
            info = get_detector_info(q, F)

        info.y /= info.y.max()
        return SaxsInfo(space, ft_image, info)

    def draw_saxs(self, saxs_info):
        """
        Draw a shape in the electron density space.

        Parameters
        ----------
        shape_condition : np.ndarray
            A boolean array representing the shape to be drawn.
        """

        fig = plt.figure(figsize=(12,3))
        ax1 = fig.add_subplot(141, projection="3d")
        ax2 = fig.add_subplot(142, projection="3d")
        ax3 = fig.add_subplot(143)
        ax4 = fig.add_subplot(144)
        ax4.set_yscale("log")
        ax1.set_title("Real Space Image")
        ax2.set_title("Resiprocal Space Image $abs(F)^2$")
        ax3.set_title("Detector Image")
        ax4.set_title("Scattering Curve")
        draw_voxles_as_dots(ax1, saxs_info.electron_density)
        draw_voxles_as_dots(ax2, saxs_info.ft_image**2)
        info = saxs_info.detector_info
        draw_detector_image(ax3, info.q, info.y)
        ax4.set_xlabel("q")
        ax4.set_ylabel("I(q)")
        ax4.plot(info.q, info.y)
        ax1.set_xlim(ax2.get_xlim())
        ax1.set_ylim(ax2.get_ylim())
        ax1.set_zlim(ax2.get_zlim())
        fig.tight_layout()
        self.fig = fig
        return
