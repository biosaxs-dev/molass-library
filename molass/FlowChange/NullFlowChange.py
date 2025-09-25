"""
FlowChange.NullFlowChange.py
"""
import numpy as np
from scipy.stats import linregress

class CsProxy:
    """A proxy class for Cs similarity computation.

    Attributes
    ----------
    slope : float
        The slope of the linear regression line.
    intercept : float
        The intercept of the linear regression line.
    mapped_info : MappingInfo or None
        The mapping information, computed on demand.
    a_curve : Curve or None
        The A-curve.
    x_curve : Curve or None
        The X-curve.
    """
    def __init__(self, slope, intercept, a_curve=None, x_curve=None):
        """Initializes the CsProxy with given slope and intercept.

        Parameters
        ----------
        slope : float
            The slope of the linear regression line.
        intercept : float
            The intercept of the linear regression line.
        a_curve : Curve or None, optional
            The A-curve. If None, no A-curve is associated.
        x_curve : Curve or None, optional
            The X-curve. If None, no X-curve is associated.
        """
        self.slope = slope
        self.intercept = intercept
        self.a_curve = a_curve
        self.x_curve = x_curve
        self.mapped_info = None

    def compute_whole_similarity(self):
        """Computes the whole similarity.

        Returns
        -------
        float
            The whole similarity value.
        """
        # set the highest similarity to avoid reconstructing Cs
        return 1.0

    def get_mapped_info(self):
        """Gets the mapping information, computing it if necessary.

        Returns
        -------
        MappingInfo
            The mapping information.
        """ 
        if self.mapped_info is None:
            # task: consider moving this to __init__ and improve mapping if necessary
            from molass_legacy.Mapping.PeakMapper import PeakMapper
            pm = PeakMapper(self.a_curve, self.x_curve)
            self.mapped_info = pm.mapped_info
        return self.mapped_info

class NullFlowChange:
    """A class representing a null flow change.

    Attributes
    ----------
    a_curve : Curve
        The A-curve.
    a_curve2 : Curve
        The second A-curve.
    x_curve : Curve
        The X-curve.
    cs : CsProxy or None
        The CsProxy object for similarity computation, computed on demand.
    """
    def __init__(self, a_curve, a_curve2, x_curve):
        """Initializes the NullFlowChange with given curves.
        Parameters
        ----------
        a_curve : Curve
            The A-curve.
        a_curve2 : Curve
            The second A-curve.
        x_curve : Curve
            The X-curve.
        """
        self.a_curve = a_curve
        self.a_curve2 = a_curve2
        self.x_curve = x_curve
        self.cs = None

    def get_similarity(self):
        """Gets the similarity value.

        Returns
        -------
        float
            The similarity value.
        """
        if self.cs is None:
            X = self.x_curve.x[[0,-1]]
            Y = self.a_curve.x[[0,-1]]
            slope, intercept = linregress(X, Y)[0:2]
            self.cs = CsProxy(slope, intercept, a_curve=self.a_curve, x_curve=self.x_curve)
        return self.cs

    def get_real_flow_changes(self):
        """Gets the real flow changes.

        Returns
        -------
        None, None
            Indicates no real flow changes.
        """
        return None, None
    
    def has_special(self):
        """Indicates whether there are special flow changes.

        Returns
        -------
        bool
            Always returns False.
        """
        return False
    
    def remove_irregular_points(self):
        """Removes irregular points.
        
        Returns
        -------
        array, array, slice
            Empty arrays and a full slice.
        """
        return np.array([]), np.array([]), slice(None, None)