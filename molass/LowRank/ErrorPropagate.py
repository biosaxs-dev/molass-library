"""
    LwRank.ErrorPropagate.py

    This module is used to propagate the error of the low rank approximation.

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np

def compute_propagated_error(M, P, E):
    """
    Compute the propagated error of the low rank approximation.
    """
    M_pinv = np.linalg.pinv(M)
    W = np.dot(M_pinv, P)
    Pe = np.sqrt(np.dot(E**2, W**2))
    return Pe