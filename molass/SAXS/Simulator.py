"""
# This module contains the SAXS simulator class.

"""
import numpy as np
import matplotlib.pyplot as plt
from learnsaxs import draw_voxles_as_dots, draw_detector_image
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

    def get_curve(self):
        """
        Get the SAXS scattering curve from the detector information.
        """
        from molass.DataObjects import Curve
        return Curve(self.detector_info.q, self.detector_info.y, type='j')

def compute_saxs(rho, q=None, dmax=None, use_denss=False, debug=True):
    if debug:
        from importlib import reload
        import molass.SAXS.DenssTools
        reload(molass.SAXS.DenssTools)
    from .DenssTools import get_detector_info_from_density
    if q is None:
        q = np.linspace(0.005, 0.5, 100)

    if dmax is None:
        # Default dmax is half the size of the density space
        # This is a common choice for SAXS simulations
        # It can be adjusted based on the specific requirements of the simulation
        # or the characteristics of the sample being studied.
        # Here, we assume rho is a 3D numpy array.
        dmax = rho.shape[0] * 0.5
    info, ft_image = get_detector_info_from_density(q, rho, dmax=dmax, use_denss=use_denss)
    info.y /= info.y.max()
    return SaxsInfo(rho, ft_image, info)

def draw_saxs(saxs_info):
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
    return fig

