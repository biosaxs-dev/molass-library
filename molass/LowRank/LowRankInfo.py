"""
    LowRank.LowRankInfo.py

    This module contains the class LowRankInfo, which is used to store information
    about the components of a SecSaxsData, which is mathematically interpreted as
    a low rank approximation of a matrix.
"""
from importlib import reload
import numpy as np
import matplotlib.pyplot as plt

def get_denoised_data( D, rank=3, svd=None ):
    """
    Get the denoised data by low rank approximation using SVD.

    Parameters
    ----------
    D : 2D array-like
        The data matrix to be denoised.
    rank : int, optional
        The rank for the low rank approximation, by default 3.
    svd : tuple or None, optional
        Precomputed SVD (U, s, VT) to use instead of computing it again

    Returns
    -------
    D_ : 2D array-like
        The denoised data matrix.
    """
    # print( 'get_denoised_data: rank=', rank )
    if svd is None:
        U, s, VT = np.linalg.svd( D )
    else:
        U, s, VT = svd
    if s.shape[0] > rank:
        Us_ = np.dot( U[:,0:rank], np.diag( s[0:rank] ) )
        D_  = np.dot( Us_, VT[0:rank,:] )
    else:
        # just make a copy
        # although this case might better be avoided
        D_  = np.array(D)
    return D_

def compute_lowrank_matrices(M, ccurves, E, ranks, **kwargs):
    """
    Compute the matrices for the low rank approximation.
    The low rank approximation is computed using the formula:
        M_ = P @ C
    where M_ is the denoised data matrix, P is the projected matrix,
    and C is the component matrix.
    Parameters
    ----------
    M : 2D array-like
        The data matrix to be approximated.
    ccurves : list of ComponentCurve
        The list of component curves.
    E : 2D array-like or None
        The error matrix corresponding to M. It can be None if errors are not available.
    ranks : list of int or None
        The list of ranks for each component curve. If None, all ranks are assumed to be 1.
    kwargs : dict, optional
        Additional keyword arguments for the low rank approximation.
        Possible keys include:
            - svd_rank: int or None
                The rank for the SVD used in the low rank approximation. If None, it will be set to the sum of ranks.
    Returns
    -------
    M_ : 2D array-like
        The denoised data matrix.
    C : 2D array-like
        The concentration matrix.
    P : 2D array-like
        The spectral factor matrix.
    Pe : 2D array-like or None
        The propagated error matrix corresponding to P. It can be None if E is None.
    """ 
    num_components = len(ccurves)
    if ranks is None:
        ranks = [1] * num_components
    rank = np.sum(ranks)
    svd_rank = kwargs.get('svd_rank', None)
    if svd_rank is None:
        svd_rank = rank
    if svd_rank < rank:
        from molass.Except.ExceptionTypes import InadequateUseError
        raise InadequateUseError("svd_rank(%d) must not be less than number of components(%d)" % (svd_rank, rank))
    
    M_ = get_denoised_data(M, rank=svd_rank)
    cy_list = [c.get_xy()[1] for c in ccurves]
    for k, r in enumerate(ranks):
        if r > 1:
            assert r == 2, "Only rank 2 is supported"
            cy_list.append(cy_list[k] ** r)
    C = np.array(cy_list)
    P = M_ @ np.linalg.pinv(C)
    C_ = C[:num_components,:]   # ignore higher order components
    P_ = P[:,:num_components]   # ignore higher order components

    if E is None:
        Pe = None
    else:
        # propagate the error
        from molass.LowRank.ErrorPropagate import compute_propagated_error
        Pe = compute_propagated_error(M_, P_, E)
        
    return M_, C_, P_, Pe
