"""
    Stats.EghMoment.py
"""
import numpy as np
from .Moment import Moment, compute_meanstd
from molass.LowRank.CurveDecomposer import decompose_icurve_impl

class EghMoment(Moment):
    """A class to represent the Egh moment of a SAXS/UV curve.
    It decomposes the input intensity curve into multiple EGH components
    and computes the mean and standard deviation of the combined components.

    Attributes
    ----------
    icurve : IntensityCurve
        The input intensity curve.
    num_peaks : int
        The number of Gaussian peaks to fit.
    curves : list of GaussianCurve
        The list of fitted Gaussian curves.
    """
    def __init__(self, icurve, num_peaks=None):
        """Initialize the EghMoment object.

        Parameters
        ----------
        icurve : IntensityCurve
            The input intensity curve.
        num_peaks : int, optional
            The number of Gaussian peaks to fit. If None, it will be determined automatically.
        """
        super().__init__(icurve.x, icurve.y)
        self.icurve = icurve
        self.num_peaks = num_peaks

    def get_y_(self):
        """Get the computed y values from the EGH decomposition.
        
        Returns
        -------
        array-like
            The computed y values from the EGH decomposition.
        """
        if self.y_ is None:
            self.y_ = self.compute_egh_y()
        return self.y_

    def compute_egh_y(self):
        """Compute the y values from the EGH decomposition.

        Returns
        -------
        array-like
            The computed y values from the EGH decomposition.
        """
        icurve = self.icurve
        if self.num_peaks is None:
            self.num_peaks = len(icurve.get_peaks())
        self.curves = decompose_icurve_impl(icurve, self.num_peaks)   # egh component
        cy_list = []
        for curve in self.curves:
            _, cy = curve.get_xy()
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        return ty
        