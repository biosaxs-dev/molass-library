"""
    LowRank.LowRankInfo.py

    This module contains the class LowRankInfo, which is used to store information
    about the components of a SecSaxsData, which is mathematically interpreted as
    a low rank approximation of a matrix.
"""
from importlib import reload
import numpy as np
import matplotlib.pyplot as plt
from molass.LowRank.LowRankInfo import compute_lowrank_matrices

class Decomposition:
    """
    A class to store information about the components of a SecSaxsData,
    which includes the result of decomposition by LowRank.Decomposer.
    """

    def __init__(self, ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, **kwargs):
        """
        """
        assert len(xr_ccurves) == len(uv_ccurves)
        self.num_components = len(xr_ccurves)

        self.xr = ssd.xr
        self.xr_icurve = xr_icurve
        self.xr_ccurves = xr_ccurves
        self.xr_ranks = None

        self.uv = ssd.uv
        self.uv_icurve = uv_icurve
        self.uv_ccurves = uv_ccurves
        self.uv_ranks = None
 
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
            import molass.PlotUtils.DecompositionPlot
            reload(molass.PlotUtils.DecompositionPlot)
        from molass.PlotUtils.DecompositionPlot import plot_components_impl
        return plot_components_impl(self, **kwargs)

    def update_xr_ranks(self, ranks, debug=False):
        """
        Update the ranks for the X-ray data.
        """
        self.xr_ranks = ranks

    def get_xr_matrices(self, debug=False):
        """
        Get the matrices for the X-ray data.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.LowRankInfo
            reload(molass.LowRank.LowRankInfo)
        from molass.LowRank.LowRankInfo import compute_lowrank_matrices

        xr = self.xr
        return compute_lowrank_matrices(xr.M, self.xr_ccurves, xr.E, self.xr_ranks, debug=debug)

    def get_xr_components(self, debug=False):
        """
        Get the components.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.Component
            reload(molass.LowRank.Component)
        from molass.LowRank.Component import XrComponent

        xr_matrices = self.get_xr_matrices(debug=debug)
        xrC, xrP, xrPe = xr_matrices[1:]

        ret_components = []
        for i in range(self.num_components):
            icurve_array = np.array([self.xr_icurve.x, xrC[i,:]])
            jcurve_array = np.array([self.xr.qv, xrP[:,i], xrPe[:,i]]).T
            ret_components.append(XrComponent(icurve_array, jcurve_array))

        return ret_components

    def get_uv_matrices(self, debug=False):
        """
        Get the matrices for the UV data.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.LowRankInfo
            reload(molass.LowRank.LowRankInfo)
        from molass.LowRank.LowRankInfo import compute_lowrank_matrices

        uv = self.uv
        return compute_lowrank_matrices(uv.M, self.uv_ccurves, uv.E, self.uv_ranks, debug=debug)

    def get_uv_components(self, debug=False):
        """
        Get the components.
        """
        if debug:
            from importlib import reload
            import molass.LowRank.Component
            reload(molass.LowRank.Component)
        from molass.LowRank.Component import UvComponent

        uv_matrices = self.get_uv_matrices(debug=debug)
        uvC, uvP, uvPe = uv_matrices[1:]
        if uvPe is None:
            uvPe = np.zeros_like(uvP)

        ret_components = []
        for i in range(self.num_components):
            uv_elution = np.array([self.uv_icurve.x, uvC[i,:]])
            uv_spectral = np.array([self.uv.wv, uvP[:,i], uvPe[:,i]]).T
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

    def compute_scds(self, debug=False):
        """
        Get the low rank information.
        """
        if debug:
            import molass.LowRank.RankEstimator
            reload(molass.LowRank.RankEstimator)
        from molass.LowRank.RankEstimator import compute_scds_impl
        return compute_scds_impl(self.xr_icurve, self.xr_ccurves, self.uv_icurve, self.uv_ccurves, debug=debug)
    