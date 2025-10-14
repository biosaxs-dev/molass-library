"""
    Baseline.Basesurface.py
"""
import numpy as np
from molass.Baseline.Surface import Surface

def get_linear_surface(icurve, jcurve):
    """Get a linear surface from the given intensity curves.
    
    Parameters
    ----------
    icurve : IntensityCurve
        The intensity curve along the i-axis.
    jcurve : IntensityCurve
        The intensity curve along the j-axis.
        
    Returns
    -------
    surface : 2D array-like
        The linear surface defined by the outer product of the two curves.
    """
    return icurve.y[:,np.newaxis] @ jcurve.y[np.newaxis,:]
