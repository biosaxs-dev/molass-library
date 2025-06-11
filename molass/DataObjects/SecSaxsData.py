"""
    DataObjects.SecSacsData.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import os
import numpy as np
from glob import glob
from importlib import reload
import logging

class SecSaxsData:
    """
    A class to represent a SEC-SAXS data object."""

    def __init__(self, folder=None, object_list=None, uv_only=False, xr_only=False,
                 trimmed=False,
                 remove_bubbles=False,
                 beamlineinfo=None,
                 mapping=None,
                 debug=False):
        """ssd = SecSacsData(data_folder)
        
        Creates a SEC-SAXS data object.

        Parameters
        ----------
        folder : str, optional
            Specifies the folder path where the data are stored.
            It is required if the data_list parameter is ommitted.
        object_list : list, optional
            A list which includes [xr_data, uv_data]
            in this order to be used as corresponding data items.
            It is required if the folder parameter is ommitted.       
        uv_only : bool, optional
            If it is True, only UV data will be loaded
            to suppress unnecessary data access.
        xr_only : bool, optional
            If it is True, only XR data will be loaded
            to suppress unnecessary data access.
        trimmed : bool, optional
            If it is True, the data will be treated as trimmed.
        remove_bubbles : bool, optional
            If it is True, bubbles will be removed from the data.
        beamlineinfo : BeamlineInfo, optional
            If specified, the beamline information will be used.
        mapping : MappingInfo, optional
            If specified, the mapping information will be used.

        Examples
        --------
        >>> ssd = SecSacsData('the_data_folder')

        >>> uv_only_ssd = SecSacsData('the_data_folder', uv_only=True)
        """
        self.logger = logging.getLogger(__name__)
        if folder is None:
            assert object_list is not None
            xr_data, uv_data = object_list
        else:
            assert object_list is None
            if uv_only:
                xrM = None
                xrE = None
                qv = None
            else:
                if not os.path.isdir(folder):
                    raise FileNotFoundError(f"Folder {folder} does not exist.")
                
                from molass.DataUtils.XrLoader import load_xr_with_options
                xr_array = load_xr_with_options(folder, remove_bubbles=remove_bubbles, logger=self.logger)
                xrM = xr_array[:,:,1].T
                xrE = xr_array[:,:,2].T
                qv = xr_array[0,:,0]

            if xr_only:
                uvM, wv = None, None
            else:
                from molass.DataUtils.UvLoader import load_uv
                from molass.DataUtils.Beamline import get_beamlineinfo_from_settings
                uvM, wv = load_uv(folder)
                beamlineinfo = get_beamlineinfo_from_settings()
            uvE = None
 
            if xrM is None:
                xr_data = None
            else:
                from molass.DataObjects.XrData import XrData
                xr_data = XrData(qv, None, xrM, xrE)
            self.xr_data = xr_data

            if uvM is None:
                uv_data = None
            else:
                from molass.DataObjects.UvData import UvData
                uv_data = UvData(wv, None, uvM, uvE)
    
        self.xr = xr_data
        self.uv = uv_data
        self.trimming_info = None
        self.trimmed = trimmed
        self.mapping = mapping
        self.beamlineinfo = beamlineinfo

    def plot_3d(self, **kwargs):
        """ssd.plot_3d(view_init=None)

            Plots a pair of 3D figures of UV and XR data.

            Parameters
            ----------
            view_init   : dict, optional
                A dictionary which specifies the view_init parameters.
                The default is dict(elev=30, azim=-60) as of matplotlib 3.10.

            view_arrows : bool, optional
                If it is True, the 2D view arrows are drawn on the 3D plot.
                One of the arrows shows the elutional view, while the other
                shows the spectral view. The default is False.

            Rturns
            -------
            result : PlotResult
                A PlotResult object which contains the following attributes.

                fig: Figure
                axes: Axes
        """
        debug = kwargs.pop('debug', False)
        if debug:
            import molass.PlotUtils.SecSaxsDataPlot
            reload(molass.PlotUtils.SecSaxsDataPlot)
        from molass.PlotUtils.SecSaxsDataPlot import plot_3d_impl
        return plot_3d_impl(self, **kwargs)
 
    def plot_compact(self, **kwargs):
        """ssd.plot_compact()

            Plots a pair of compact figures of UV and XR data.

            Parameters
            ----------
            None

            Returns
            -------
            result : PlotResult
                A PlotResult object which contains the following attributes.

                fig: Figure
                axes: Axes
        """
        debug = kwargs.pop('debug', False)
        if debug:
            import molass.PlotUtils.SecSaxsDataPlot
            reload(molass.PlotUtils.SecSaxsDataPlot)
        from molass.PlotUtils.SecSaxsDataPlot import plot_compact_impl
        return plot_compact_impl(self, **kwargs)

    def make_trimming_info(self, **kwargs):
        """ssd.make_trimming_info(xr_qr=None, xr_mt=None, uv_wr=None, uv_mt=None, uv_fc=None)
        
        Returns a pair of indeces which should be used
        as a slice for the spectral axis to trim away
        unusable UV data regions. 

        Parameters
        ----------
        xr_qr : 

        xr_mt : 

        uv_wr : 

        uv_mt :

        uv_fc :  

        See Also
        --------
        ssd.copy()        

        Examples
        --------
        >>> trim = ssd.make_trimming_info()
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.Trimming.TrimmingUtils
            reload(molass.Trimming.TrimmingUtils)
        from molass.Trimming.TrimmingUtils import make_trimming_info_impl
        flowchange = False if self.trimmed else None
        if self.trimming_info is None:
            self.trimming_info = make_trimming_info_impl(self, flowchange=flowchange, **kwargs)
        return self.trimming_info

    def plot_baselines(self, debug=True):
        """ssd.plot_baselines()

            Plots a pair of figures of UV and XR data, which include
            baselines.

            Parameters
            ----------
            None
        """
        if debug:
            import molass.PlotUtils.SecSaxsDataPlot
            reload(molass.PlotUtils.SecSaxsDataPlot)
        from molass.PlotUtils.SecSaxsDataPlot import plot_baselines_impl
        return plot_baselines_impl(self)

    def plot_trimming_info(self, trim=None, **kwargs):
        """ssd.plot_trimming_info(trim)

        Plots a set of trimmming info.

        Parameters
        ----------
        trim : 

        title : str, optional
            If specified, add a super title to the plot.
        
        return_fig : bool, optional
            If it is True, returns the figure object.

        Returns
        -------
        result : PlotResult
            A PlotResult object which contains the following attributes.

            fig: Figure
            axes: Axes
            trimming : TrimmingInfo

        See Also
        --------
        ssd.get_trimming_info()        

        Examples
        --------
        >>> trim = ssd.get_trimming_info()
        >>>      
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.PlotUtils.TrimmingPlot
            reload(molass.PlotUtils.TrimmingPlot)
        from molass.PlotUtils.TrimmingPlot import plot_trimming_info_impl
        baseline = kwargs.pop('baseline', True)
        if trim is None:
            trim = self.make_trimming_info(**kwargs)
        return plot_trimming_info_impl(self, trim, baseline=baseline, **kwargs)

    def copy(self, xr_slices=None, uv_slices=None, trimmed=False, mapping=None):
        """ssd.copy(xr_slices=None, uv_slices=None)
        
        Returns a deep copy of this object.

        Parameters
        ----------
        xr_slices : (xr_islice, xr_jslice), optional.
            If specified, the returned copy contains the deep copies
            of elements xrM[xr_islice:xr_jslice] and qv[xr_islice].
            Otherwise, the returned copy contains the deep copies
            of elements xrM and qv.

        uv_slices : (uv_islice, uv_jslice), optional.
            If specified, the returned copy contains the deep copies
            of elements uvM[uv_islice:uv_jslice] and wv[uv_islice].
            Otherwise, the returned copy contains the deep copies
            of elements uvM and wv.

        See Also
        --------
        ssd.get_trimming_info()        

        Examples
        --------
        >>> copied_ssd = ssd.copy()

        >>> ti = ssd.get_trimming_info()
        >>> trimmed_ssd = ssd.copy(xr_slices=ti.xr_slices, uv_slices=ti.uv_slices)

        """
 
        if self.xr is None:
            xr_data = None
        else:
            xr_data = self.xr.copy(slices=xr_slices)
            
        if self.uv is None:
            uv_data = None
        else:
            uv_data = self.uv.copy(slices=uv_slices)
            
        return SecSaxsData(object_list=[xr_data, uv_data], trimmed=trimmed, beamlineinfo=self.beamlineinfo, mapping=mapping)

    def trimmed_copy(self, trim=None):
        if trim is None:
            trim = self.make_trimming_info()
        elif type(trim) is dict:
            from molass.Trimming.TrimmingInfo import TrimmingInfo
            trim = TrimmingInfo(**trim)
        return self.copy(xr_slices=trim.xr_slices, uv_slices=trim.uv_slices, trimmed=True, mapping=trim.mapping)

    def corrected_copy(self):
        """ssd.corrected_copy()
        
        Returns a deep copy of this object which has been corrected
        subtracting the baseline from the original data.
        
        Parameters
        ----------
        None
        """

        ssd_copy = self.copy(trimmed=self.trimmed, mapping=self.mapping)

        baseline = ssd_copy.xr.get_baseline2d()
        ssd_copy.xr.M -= baseline

        if ssd_copy.uv is not None:
            baseline = ssd_copy.uv.get_baseline2d()
            ssd_copy.uv.M -= baseline

        return ssd_copy
    
    def estimate_mapping(self, debug=False):
        if debug:
            import molass.Mapping.SimpleMapper
            reload(molass.Mapping.SimpleMapper)
        from molass.Mapping.SimpleMapper import estimate_mapping_impl

        if self.uv is None:
            from molass.Except.ExceptionTypes import InconsistentUseError
            raise InconsistentUseError("estimate_mapping is not for XR-only data.")

        xr_curve = self.xr.get_icurve()
        uv_curve = self.uv.get_icurve()
        self.mapping = estimate_mapping_impl(xr_curve, uv_curve, debug=debug)
        return self.mapping

    def get_mapping(self):
        """ssd.get_mapping()

        Returns the mapping information object.

        Parameters
        ----------
        None

        Returns
        -------
        mapping : MappingInfo
            A MappingInfo object which contains the mapping information.
            If the mapping information is not available, returns None.
        """
        if self.mapping is None:
            self.estimate_mapping()
        return self.mapping

    def get_concfactor(self):
        if self.beamlineinfo is None:
            return None
        else:
            return self.beamlineinfo.get_concfactor()

    def make_conc_info(self, mapping=None, **kwargs):
        debug = kwargs.get('debug', False)
        if debug:
            import molass.DataUtils.Concentration
            reload(molass.DataUtils.Concentration)
        from molass.DataUtils.Concentration import make_concinfo_impl
        return make_concinfo_impl(self, mapping, **kwargs)
    
    def quick_lowrank_info(self, num_components=None, ranks=None, **kwargs):
        """ssd.make_lowrank_info(elution_model='egh')

        Returns a lowrank information object.

        Parameters
        ----------
        num_components : int, optional
            Specifies the number of components which also implies the SVD rank
            used to denoise the matrix data.

        elution_model : str, optional
            Specifies the elution model to be used.
            The default is 'egh'.
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.LowRank.CoupledAdjuster
            reload(molass.LowRank.CoupledAdjuster)
        from molass.LowRank.CoupledAdjuster import make_lowrank_info_impl
        if num_components is None:
            if ranks is None:
                if debug:
                    import molass.LowRank.RankEstimator
                    reload(molass.LowRank.RankEstimator)
                from molass.LowRank.RankEstimator import estimate_rank
                num_components = estimate_rank(self)
                ranks = [1] * num_components
            else:
                num_components = len(ranks)
        else:
            if ranks is None:
                ranks = [1] * num_components
            else:
                if num_components != len(ranks):
                    from molass.Except.ExceptionTypes import InconsistentUseError
                    raise InconsistentUseError("The number of components and ranks should be the same.")
        return make_lowrank_info_impl(self, num_components, ranks, **kwargs)

    def inspect_ip_effect(self, debug=False):
        """ssd.inspect_ip_effect()

        Parameters
        ----------
        None
        """
        if debug:
            import molass.InterParticle.IpEffectInspect
            reload(molass.InterParticle.IpEffectInspect)
        from molass.InterParticle.IpEffectInspect import inspect_ip_effect_impl
        return inspect_ip_effect_impl(self, debug=debug)