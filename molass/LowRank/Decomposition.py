"""
    LowRank.LowRankInfo.py

    This module contains the class LowRankInfo, which is used to store information
    about the components of a SecSaxsData, which is mathematically interpreted as
    a low rank approximation of a matrix.
"""
from importlib import reload
import numpy as np

class Decomposition:
    """
    A class to store information about the components of a SecSaxsData,
    which includes the result of decomposition by LowRank.Decomposer.
    """

    def __init__(self, ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves, mapped_curve=None, paired_ranges=None, **kwargs):
        """
        """
        assert len(xr_ccurves) == len(uv_ccurves)
        self.num_components = len(xr_ccurves)
        self.ssd = ssd

        self.xr = ssd.xr
        self.xr_icurve = xr_icurve
        self.xr_ccurves = xr_ccurves
        self.xr_ranks = None

        self.uv = ssd.uv
        self.uv_icurve = uv_icurve
        self.uv_ccurves = uv_ccurves
        self.uv_ranks = None
 
        self.mapping = ssd.get_mapping()
        self.mapped_curve = mapped_curve
        self.paired_ranges = paired_ranges

    def copy_with_new_components(self, xr_ccurves, uv_ccurves):
        """
        Create a new Decomposition with new component curves.
        """
        return Decomposition(self.ssd, self.xr_icurve, xr_ccurves, self.uv_icurve, uv_ccurves, self.mapped_curve, self.paired_ranges)

    def get_num_components(self):
        """
        Get the number of components.
        """
        return self.num_components

    def plot_components(self, **kwargs):
        """
        Plot the components.
        """
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.PlotUtils.DecompositionPlot
            reload(molass.PlotUtils.DecompositionPlot)
        from molass.PlotUtils.DecompositionPlot import plot_components_impl, ALLOWED_KEYS
        for key in kwargs.keys():
            if key not in ALLOWED_KEYS:
                raise ValueError(f"Invalid key: {key}. Allowed keys are: {ALLOWED_KEYS}")
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
            ccurve = self.xr_ccurves[i]
            ret_components.append(XrComponent(icurve_array, jcurve_array, ccurve))

        return ret_components

    def get_guinier_objects(self):
        """
        Get the list of Guinier objects for the XR components.
        """
        xr_components = self.get_xr_components()
        return [c.get_guinier_object() for c in xr_components]
    
    def get_rgs(self):
        """
        Get the list of Rg values for the XR components.
        """
        xr_components = self.get_xr_components()
        return [c.compute_rg() for c in xr_components]

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
            ccurve = self.uv_ccurves[i]
            ret_components.append(UvComponent(uv_elution, uv_spectral, ccurve))

        return ret_components

    def get_pairedranges(self, mapped_curve=None, area_ratio=0.7, concentration_datatype=2, debug=False):
        """
        Get the paired ranges.
        """
        if self.paired_ranges is None:
            if debug:
                import molass.Reports.ReportRange
                reload(molass.Reports.ReportRange)
            from molass.Reports.ReportRange import make_v1report_ranges_impl
            if mapped_curve is None:
                if self.mapped_curve is None:
                    from molass.Backward.MappedCurve import make_mapped_curve
                    self.mapped_curve = make_mapped_curve(self.ssd, debug=debug)
                mapped_curve = self.mapped_curve
            self.paired_ranges = make_v1report_ranges_impl(self, self.ssd, mapped_curve, area_ratio, concentration_datatype, debug=debug)
        return self.paired_ranges

    def get_proportions(self):
        """
        Get the proportions of the components.
        """
        n = self.get_num_components()
        props = np.zeros(n)
        for i, c in enumerate(self.get_xr_components()):
            props[i] = c.compute_area()
        return props/np.sum(props)

    def compute_scds(self, debug=False):
        """
        Get the list of SCDs (Score of Concentration Dependence) for the decomposition.
        """
        if debug:
            import molass.Backward.RankEstimator
            reload(molass.Backward.RankEstimator)
        from molass.Backward.RankEstimator import compute_scds_impl
        return compute_scds_impl(self, debug=debug)
    
    def get_cd_color_info(self):
        """
        Get the color information for the concentration dependence.
        """
        if self.xr_ranks is None:
            import logging
            logging.warning("Decomposition.get_cd_color_info: xr_ranks is None, using default ranks.")
            ranks = [1] * self.num_components
        else:
            ranks = self.xr_ranks

        peak_top_xes = [ccurve.get_peak_top_x() for ccurve in self.xr_ccurves]
        scd_colors = ['green' if rank == 1 else 'red' for rank in ranks]
        return peak_top_xes, scd_colors
    
    def optimize_with_model(self, model_name, debug=False):
        """
        Optimize the decomposition with a model.
        """
        if debug:
            import molass.SEC.ModelFactory
            reload(molass.SEC.ModelFactory)
        from molass.SEC.ModelFactory import create_model
        model = create_model(model_name, debug=debug)
        return model.optimize_decomposition(self, debug=debug)

