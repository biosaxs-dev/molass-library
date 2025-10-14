"""
    LwRank.ErrorPropagate.py

    This module is used to propagate the error of the low rank approximation.
"""
import numpy as np

def compute_propagated_error(M, P, E):
    """
    Compute the propagated error of the low rank approximation.
    The propagated error Pe is computed using the formula:
        Pe = sqrt( (E^2) * (W^2) )

    Parameters
    ----------
    M : 2D array-like
        The matrix used for the low rank approximation.
    P : 2D array-like
        The projected matrix.
    E : 2D array-like
        The error matrix corresponding to M.
        
    Returns
    -------
    Pe : 2D array-like
        The propagated error matrix corresponding to P.
    """
    M_pinv = np.linalg.pinv(M)
    W = np.dot(M_pinv, P)
    Pe = np.sqrt(np.dot(E**2, W**2))
    return Pe