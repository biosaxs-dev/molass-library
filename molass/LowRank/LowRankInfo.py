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
