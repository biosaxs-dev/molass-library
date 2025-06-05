"""
    LowRank.LowRankInfo.py

    This module contains the class LowRankInfo, which is used to store information
    about the components of a SecSaxsData, which is mathematically interpreted as
    a low rank approximation of a matrix.

    Copyright (c) 2025, SAXS Team, KEK-PF
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

def compute_lowrank_matrices(M, ccurves, E=None, **kwargs):
    """
    Compute the matrices for the low rank approximation.
    """
    rank = len(ccurves)
    svd_rank = kwargs.get('svd_rank', None)
    if svd_rank is None:
        svd_rank = rank
    if svd_rank < rank:
        from molass.Except.ExceptionTypes import InadequateUseError
        raise InadequateUseError("svd_rank(%d) must not be less than number of components(%d)" % (svd_rank, rank))
    
    M_ = get_denoised_data(M, rank=svd_rank)
    C = np.array([c.get_xy()[1] for c in ccurves])
    P = M_ @ np.linalg.pinv(C)
    if E is not None:
        # propagate the error
        from molass.LowRank.ErrorPropagate import compute_propagated_error
        Pe = compute_propagated_error(M_, P, E)
    else:
        Pe = None
    return M_, C, P, Pe

class LowRankInfo:
    """
    A class to store information about the components of a SecSaxsData,
    which includes the result of decomposition by LowRank.Decomposer.
    """

    def __init__(self, ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs):
        """
        """

        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.LowRank.ErrorPropagate
            reload(molass.LowRank.ErrorPropagate)
        from molass.LowRank.ErrorPropagate import compute_propagated_error
        assert len(xr_ccurves) == len(uv_ccurves)
        self.rank = len(xr_ccurves)
        self.qv = ssd.xr.qv
        self.xr_icurve = xr_icurve
        self.xr_ccurves = xr_ccurves
        self.xr_matrices = compute_lowrank_matrices(ssd.xr.M, xr_ccurves, E=ssd.xr.E, **kwargs)
    
        self.wv = ssd.uv.wv
        self.uv_icurve = uv_icurve
        self.uv_ccurves = uv_ccurves
        self.uv_matrices = compute_lowrank_matrices(ssd.uv.M, uv_ccurves, E=ssd.uv.E, **kwargs)

        self.mapping = ssd.mapping

    def get_num_components(self):
        """
        Get the number of components.
        """
        return self.rank

    def plot_components(self, **kwargs):
        """
        Plot the components.
        """
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.PlotUtils.LowRankInfoPlot
            reload(molass.PlotUtils.LowRankInfoPlot)
        from molass.PlotUtils.LowRankInfoPlot import plot_components_impl
        return plot_components_impl(self, **kwargs)

    def get_xr_components(self, debug=False):
        """
        Get the components.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.Component
            reload(molass.LowRank.Component)
        from molass.LowRank.Component import XrComponent

        xrC, xrP, xrPe = self.xr_matrices[1:]

        ret_components = []
        for i in range(self.rank):
            icurve_array = np.array([self.xr_icurve.x, xrC[i,:]])
            jcurve_array = np.array([self.qv, xrP[:,i], xrPe[:,i]]).T
            ret_components.append(XrComponent(icurve_array, jcurve_array))

        return ret_components

    def get_uv_components(self, debug=False):
        """
        Get the components.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.Component
            reload(molass.LowRank.Component)
        from molass.LowRank.Component import UvComponent

        uvC, uvP, uvPe = self.uv_matrices[1:]
        if uvPe is None:
            uvPe = np.zeros_like(uvP)

        ret_components = []
        for i in range(self.rank):
            uv_elution = np.array([self.uv_icurve.x, uvC[i,:]])
            uv_spectral = np.array([self.wv, uvP[:,i], uvPe[:,i]]).T
            ret_components.append(UvComponent(uv_elution, uv_spectral))

        return ret_components

    def make_v1report_ranges(self, area_ratio=0.8, debug=False):
        """
        """
        if debug:
            import molass.Reports.ReportUtils
            reload(molass.Reports.ReportUtils)
        from molass.Reports.ReportUtils import make_v1report_ranges_impl
        return make_v1report_ranges_impl(self, area_ratio, debug=debug)
    
    def get_proportions(self):
        """
        Get the proportions of the components.
        """
        n = self.get_num_components()
        props = np.zeros(n)
        for i, c in enumerate(self.get_components()):
            props[i] = c.compute_xr_area()
        return props/np.sum(props)