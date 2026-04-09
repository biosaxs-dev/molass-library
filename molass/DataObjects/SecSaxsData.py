"""
    DataObjects.SecSacsData.py
"""
import os
import numpy as np
from glob import glob
from time import time
from importlib import reload
import logging
from molass_legacy._MOLASS.SerialSettings import set_setting

def _baseline_selftest(M, recognition_curve):
    """Baseline self-test: detect buffer-frame contamination.

    Compares per-q-row negative fraction in the peak region between a
    buffer-mean-flat baseline (uses Otsu-classified buffer frames) and an
    endpoint-linear baseline (uses only the first and last frame).

    If using buffer information produces *more* negatives than the simple
    endpoint reference, the buffer frames are likely contaminated.

    Returns the one-sided Wilcoxon signed-rank p-value, or None if the
    test cannot be computed (too few q-rows with nonzero difference).
    """
    from scipy.stats import wilcoxon
    from molass.Baseline.BuffitBaseline import _otsu_threshold

    rc_y = recognition_curve.y
    normalized = (rc_y - rc_y.min()) / (rc_y.max() - rc_y.min() + 1e-30)
    otsu_thr = _otsu_threshold(normalized)
    buffer_mask = normalized < otsu_thr
    peak_mask = ~buffer_mask

    if peak_mask.sum() < 2 or buffer_mask.sum() < 2:
        return None

    n_q, n_f = M.shape

    # Endpoint-linear baseline (2-point per q-row)
    bl_endpoint = np.empty_like(M)
    for i in range(n_q):
        bl_endpoint[i, :] = np.linspace(M[i, 0], M[i, -1], n_f)

    # Buffer-mean flat baseline
    buf_mean = M[:, buffer_mask].mean(axis=1)
    bl_bufmean = buf_mean[:, None] * np.ones((1, n_f))

    # Per-q-row negative-fraction difference
    peak_cols = np.where(peak_mask)[0]
    per_q_nf = np.empty(n_q)
    for i in range(n_q):
        row_peak_ep = M[i, peak_cols] - bl_endpoint[i, peak_cols]
        row_peak_bm = M[i, peak_cols] - bl_bufmean[i, peak_cols]
        nf_ref = np.mean(row_peak_ep < 0)
        nf_test = np.mean(row_peak_bm < 0)
        per_q_nf[i] = nf_test - nf_ref

    nonzero = per_q_nf[per_q_nf != 0]
    if len(nonzero) < 10:
        return None

    _, p_value = wilcoxon(nonzero, alternative='greater')
    return float(p_value)

class SecSaxsData:
    """
    A class to represent a SEC-SAXS data object.
    It contains a pair of :class:`~molass.DataObjects.XrData` and :class:`~molass.DataObjects.UvData` objects.
    It also contains the beamline information and mapping information if available.

    Attributes
    ----------
    xr : XrData or None
        The XR data object.
    uv : UvData or None
        The UV data object.
    trimmed : bool
        Indicates whether the data has been trimmed.
        This attribute is used to avoid minor redundant trimming operations which may cause inconsistency from the algorithmic reasons.
    mapping : MappingInfo or None
        The mapping information between XR and UV data.
    beamline_info : BeamlineInfo or None
        The beamline information.
    time_initialized : float
        The time when the object was initialized.
    time_required : float
        The time required for processing the data.
    time_required_total : float
        The total time required for processing all data. This includes the time required for processing the data
    datafiles : list of str or None
        The list of data files used for the analysis.
    logger : logging.Logger
        The logger object for logging messages.

    """

    def __init__(self, folder=None, object_list=None, uv_only=False, xr_only=False,
                 trimmed=False,
                 trimming=None,
                 remove_bubbles=False,
                 beamline_info=None,
                 mapping=None,
                 time_initialized=None,
                 datafiles=None,
                 uv_pickat=None,
                 uv_monitor=None,
                 xr_pickat=None,
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
        beamline_info : BeamlineInfo, optional
            If specified, the beamline information will be used.
        mapping : MappingInfo, optional
            If specified, the mapping information will be used.
        time_initialized : float, optional
            If specified, the time when the object was initialized.
            If it is None, the time will be set to the time taken for initialization.
        datafiles : list of str, optional
            If specified, the list of data files used for the analysis.
            If it is None, the data files will be set to the list of files loaded from the folder.
        uv_pickat : float, optional
            The wavelength (nm) at which to extract the UV elution profile.
            Defaults to 280 nm when None. Use 290 for samples like ATP or MY
            where the UV signal is measured at 290 nm.
        uv_monitor : float, optional
            Alias for ``uv_pickat``. Follows chromatography convention
            ("monitoring wavelength"). If both are given, ``uv_monitor`` wins.
        xr_pickat : float, optional
            The q-value (Å⁻¹) at which to extract the XR elution profile.
            Defaults to 0.02 when None.
        debug : bool, optional
            If True, enables debug mode for more verbose output.

        Examples
        --------
        >>> ssd = SecSacsData('the_data_folder')

        >>> uv_only_ssd = SecSacsData('the_data_folder', uv_only=True)
        """
        start_time = time()
        self.logger = logging.getLogger(__name__)
        if folder is None:
            assert object_list is not None
            xr_data, uv_data = object_list
            self.datafiles = datafiles
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
                xr_array, datafiles = load_xr_with_options(folder, remove_bubbles=remove_bubbles, logger=self.logger)
                xrM = xr_array[:,:,1].T
                xrE = xr_array[:,:,2].T
                qv = xr_array[0,:,0]
                set_setting('in_folder', folder)    # for backward compatibility
                self.datafiles = datafiles

            if xr_only:
                uvM, wv = None, None
            else:
                from molass.DataUtils.UvLoader import load_uv
                from molass.DataUtils.Beamline import get_beamlineinfo_from_settings
                uvM, wv, conc_file = load_uv(folder, return_also_conc_file=True)
                beamline_info = get_beamlineinfo_from_settings()
                set_setting('uv_folder', folder)    # for backward compatibility
                set_setting('uv_file', conc_file)   # for backward compatibility
            uvE = None
 
            if xrM is None:
                xr_data = None
            else:
                from molass.DataObjects.XrData import XrData
                xr_data = XrData(xrM, qv, None, xrE)
            self.xr_data = xr_data

            if uvM is None:
                uv_data = None
            else:
                from molass.DataObjects.UvData import UvData
                uv_data = UvData(uvM, wv, None, uvE)
    
        self.xr = xr_data
        self.uv = uv_data
        effective_uv_pickat = uv_monitor if uv_monitor is not None else uv_pickat
        if effective_uv_pickat is not None and self.uv is not None:
            self.uv.pickat = effective_uv_pickat
        if xr_pickat is not None and self.xr is not None:
            self.xr.pickat = xr_pickat
        self.trimmed = trimmed
        self.trimming = trimming
        self.mapping = mapping
        self.beamline_info = beamline_info
        if time_initialized is None:
            self.time_initialized = time() - start_time
        else:
            self.time_initialized = time_initialized
        self.time_required = self.time_initialized          # updated later in trimmed_copy() or corrected_copy()
        self.time_required_total = self.time_initialized    # updated later in trimmed_copy() or corrected_copy()

    def __repr__(self):
        parts = []
        if self.xr is not None:
            parts.append(f"xr={self.xr.M.shape[1]} frames")
        if self.uv is not None:
            parts.append(f"uv={self.uv.M.shape[1]} frames, pickat={self.uv.pickat}")
        parts.append(f"trimmed={self.trimmed}")
        return f"SecSaxsData({', '.join(parts)})"

    def has_xr(self):
        """ssd.has_xr()

        Returns whether the XR data is available.

        Parameters
        ----------
        None

        Returns
        -------
        has_xr : bool
            True if the XR data is available, False otherwise.
        """
        return self.xr is not None

    def has_uv(self):
        """ssd.has_uv()

        Returns whether the UV data is available.

        Parameters
        ----------
        None

        Returns
        -------
        has_uv : bool
            True if the UV data is available, False otherwise.
        """
        return self.uv is not None

    def plot_3d(self, **kwargs):
        """ssd.plot_3d(title=None, view_init=None, view_arrows=False, with_2d_section_lines=False, **kwargs)

            Plots a pair of 3D figures of UV and XR data.

            Parameters
            ----------
            title : str, optional
                If specified, add a super title to the plot.
                
            view_init   : dict, optional
                A dictionary which specifies the view_init parameters.
                The default is dict(elev=30, azim=-60) as of matplotlib 3.10.

            view_arrows : bool, optional
                If it is True, the 2D view arrows are drawn on the 3D plot.
                One of the arrows shows the elutional view, while the other
                shows the spectral view. The default is False.

            with_2d_section_lines : bool, optional
                If it is True, the 2D section lines are drawn on the 3D plot.
                The default is False.

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
        from molass.PlotUtils.SecSaxsDataPlot import plot_3d_impl
        return plot_3d_impl(self, **kwargs)
 
    def plot_compact(self, **kwargs):
        """ssd.plot_compact(title=None, baseline=False, ratio_curve=None, moment_lines=False, **kwargs)

            Plots a pair of compact figures of UV and XR data.

            Parameters
            ----------
            title : str, optional
                If specified, add a super title to the plot.
            baseline : bool, optional
                If it is True, the baseline will be plotted.
            ratio_curve : Curve, optional    
                If specified, the ratio curve will be plotted.
            moment_lines : bool, optional
                If it is True, the moment lines will be plotted.

            Returns
            -------
            result : PlotResult
                A PlotResult object which contains the following attributes.

                fig: Figure
                axes: Axes
                mapping: MappingInfo (if available)
                xr_curve: Curve (if available)
                uv_curve: Curve (if available)
                mp_curve: Curve (if available)
                moment: Moment of the XR data (if available)
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.PlotUtils.SecSaxsDataPlot
            reload(molass.PlotUtils.SecSaxsDataPlot)
        from molass.PlotUtils.SecSaxsDataPlot import plot_compact_impl
        return plot_compact_impl(self, **kwargs)

    def make_trimming(self, **kwargs):
        """ssd.make_trimming(xr_qr=None, xr_mt=None, uv_wr=None, uv_mt=None)
        
        Returns a pair of indeces which should be used
        as slices for the spectral axis and the temporal axis
        to trim the data.

        Parameters
        ----------
        xr_qr : tuple of (int, int), optional
            The angular range (start, stop) to be used for the XR data.
            If it is None, the full range will be used.
        xr_mt : tuple of (int, int), optional
            The temporal range (start, stop) to be used for the XR data.
            If it is None, the full range will be used.
        uv_wr : tuple of (int, int), optional
            The wavelength range to be used for the UV data.
            If it is None, the full range will be used.
        uv_mt : tuple of (int, int), optional
            The temporal range (start, stop) to be used for the UV data.
            If it is None, the full range will be used.

        Returns
        -------
        trimming : TrimmingInfo
            A TrimmingInfo object which contains the trimming information.

        See Also
        --------
        ssd.copy()        

        Examples
        --------
        >>> trim = ssd.make_trimming()
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.Trimming.TrimmingUtils
            reload(molass.Trimming.TrimmingUtils)
        from molass.Trimming.TrimmingUtils import make_trimming_impl
        flowchange = False if self.trimmed else None
        return make_trimming_impl(self, flowchange=flowchange, **kwargs)

    def plot_trimming(self, trim=None, baseline=False, title=None, **kwargs):
        """ssd.plot_trimming(trim=None, baseline=False, title=None, return_fig=False, **kwargs)

        Plots a set of trimming info.

        Parameters
        ----------
        trim : TrimmingInfo or dict, optional
            The trimming information to be used for the plot.

        baseline : bool, optional
            If it is True, the baseline will be plotted.

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
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.PlotUtils.TrimmingPlot
            reload(molass.PlotUtils.TrimmingPlot)
        from molass.PlotUtils.TrimmingPlot import plot_trimming_impl
        if trim is None:
            trim = self.make_trimming(**kwargs)
        return plot_trimming_impl(self, trim, baseline=baseline, title=title, **kwargs)

    def copy(self, xr_slices=None, uv_slices=None, trimmed=False, trimming=None, mapping=None, datafiles=None):
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

        Returns
        -------
        SecSaxsData
            A deep copy of the SSD object with the specified slices applied.

        Examples
        --------
        >>> copied_ssd = ssd.copy()
        >>> trimming = ssd.make_trimming()
        >>> trimmed_ssd = ssd.copy(xr_slices=trimming.xr_slices, uv_slices=trimming.uv_slices)

        """
 
        if self.xr is None:
            xr_data = None
        else:
            xr_data = self.xr.copy(slices=xr_slices)
            
        if self.uv is None:
            uv_data = None
        else:
            uv_data = self.uv.copy(slices=uv_slices)
            
        return SecSaxsData(object_list=[xr_data, uv_data], trimmed=trimmed, trimming=trimming,
                           beamline_info=self.beamline_info, mapping=mapping, 
                           time_initialized=self.time_initialized, datafiles=datafiles)

    def trimmed_copy(self, trimming=None, jranges=None, mapping=None, nsigmas=None):
        """ssd.trimmed_copy(trimming=None, jranges=None, mapping=None, nsigmas=None)

        Parameters
        ----------
        trimming : TrimmingInfo, optional
            If specified, the trimming information will be used for the copy.
        jranges : tuple of (double, double), optional
            The temporal ranges to apply for trimming in the form of [(start1, end1), (start2, end2)].
        mapping : MappingInfo, optional
            If specified, the mapping information will be used for the copy.
            It must be provided if `jranges` is specified.
        nsigmas : int or float, optional
            If specified, passed to make_trimming() to control the σ-window width.

        Returns
        -------
        SecSaxsData
            A trimmed copy of the SSD object with the specified trimming specification applied.
        """
        start_time = time()
        if trimming is None:
            if nsigmas is not None:
                trimming = self.make_trimming(nsigmas=nsigmas, debug=False)
            else:
                trimming = self.make_trimming(jranges=jranges, mapping=mapping, debug=False)
        else:
            assert jranges is None, "jranges must be None if trimming is specified."
            assert nsigmas is None, "nsigmas must be None if trimming is specified."
        result = self.copy(xr_slices=trimming.xr_slices, uv_slices=trimming.uv_slices,
                           trimmed=True, trimming=trimming,
                           mapping=mapping,
                           datafiles=self.datafiles)
        result.time_required = time() - start_time
        result.time_required_total = self.time_required_total + result.time_required
        return result

    def set_baseline_method(self, method):
        """ssd.set_baseline_method(method)

        Sets the baseline method to be used for the baseline correction.

        See also: `Baseline Correction <https://biosaxs-dev.github.io/molass-tutorial/chapters/04/data_correction.html>`_

        Parameters
        ----------
        method : str or (str, str)
            Specifies the baseline method to be used.
            If it is a string, it will be used for both XR and UV data.
            If it is a tuple of two strings, the first string will be used for XR data
            and the second string will be used for UV data.

            The available methods are:

            - ``linear`` : Linear baseline (default)
            - ``uvdiff`` : UV differential method (for UV data only)
            - ``integral`` : Integral method

        Returns
        -------
        None
        """
        if isinstance(method, str):
            method = (method, method)
        if self.xr is not None:
            self.xr.set_baseline_method(method=method[0])
        if self.uv is not None:
            self.uv.set_baseline_method(method=method[1])

    def get_baseline_method(self):
        """ssd.get_baseline_method()

        Returns the baseline method used for the baseline correction.

        See also: `Baseline Correction <https://biosaxs-dev.github.io/molass-tutorial/chapters/04/data_correction.html>`_

        Parameters
        ----------
        None

        Returns
        -------
        method : (str, str)
            A tuple of two strings which contains the baseline methods used for XR and UV data.
            If the baseline method is the same for both XR and UV data,
            it returns a single string instead of a tuple.
        """
        xr_method = self.xr.get_baseline_method() if self.xr is not None else None
        uv_method = self.uv.get_baseline_method() if self.uv is not None else None
        if xr_method == uv_method:
            ret_method = xr_method
        else:
            ret_method = (xr_method, uv_method)
        return ret_method

    def set_anomaly_mask(self, mask=None):
        """Declare that this dataset contains anomalous frames to exclude from baseline fitting.

        Delegates to ``self.xr.set_anomaly_mask()`` (and ``self.uv``
        if present).  See :meth:`SsMatrixData.set_anomaly_mask` for
        full documentation.

        .. note::
            For mild anomalies, prefer ``allow_negative_peaks=True`` in
            ``quick_decomposition()`` instead.  This method excludes frames
            from the data matrix and can be too aggressive for some datasets.
            Use ``ssd.xr.get_icurve()`` after calling this to verify the
            signal is not destroyed.

        Parameters
        ----------
        mask : array-like of bool, slice, or None, optional
            Frames to exclude.  When a ``slice`` is given, start/stop are
            interpreted as frame numbers.
        """
        import numpy as np
        # Capture pre-mask signal range for safety check
        pre_range = np.ptp(self.xr.get_icurve().y)

        self.xr.set_anomaly_mask(mask=mask)
        if self.uv is not None:
            self.uv.set_anomaly_mask(mask=mask)

        # Safety check: warn if signal was drastically reduced (issue #75)
        post_range = np.ptp(self.xr.get_icurve().y)
        if pre_range > 0 and post_range / pre_range < 0.1:
            import warnings
            warnings.warn(
                f"XR signal range dropped by {(1 - post_range/pre_range)*100:.0f}% after anomaly masking "
                f"({pre_range:.2e} -> {post_range:.2e}). The mask may be too aggressive. "
                f"Consider using allow_negative_peaks=True in quick_decomposition() instead.",
                stacklevel=2,
            )

    def set_allow_negative_peaks(self, value=True, mask=None):
        """Deprecated: use ``set_anomaly_mask(mask)`` instead."""
        import warnings
        warnings.warn(
            "set_allow_negative_peaks() is deprecated; use set_anomaly_mask(mask) instead.",
            DeprecationWarning, stacklevel=2,
        )
        if value:
            self.set_anomaly_mask(mask=mask)
        else:
            self.xr.has_anomaly_mask = False
            self.xr.anomaly_mask = None
            if self.uv is not None:
                self.uv.has_anomaly_mask = False
                self.uv.anomaly_mask = None

    def corrected_copy(self, baseline=None, debug=False, **baseline_kwargs):
        """ssd.corrected_copy()
        
        Returns a deep copy of this object which has been corrected
        subtracting the baseline from the original data.
        
        Parameters
        ----------
        baseline : ndarray or None, optional
            Pre-computed 2D baseline array for XR data (same shape as
            ``ssd.xr.M``).  When provided, this baseline is used directly
            instead of computing one via :meth:`get_baseline2d`.
            **Note**: applies to XR only — the UV baseline is always
            computed internally.
        debug : bool, optional
            If True, enables debug mode for more verbose output.
        **baseline_kwargs :
            Additional keyword arguments forwarded to :meth:`get_baseline2d`
            for both XR and UV.

        Returns
        -------
        SecSaxsData
            A deep copy of the SSD object with the baseline correction applied.

        Examples
        --------
        >>> corrected = ssd.corrected_copy()                          # standard LPM
        >>> ssd.set_anomaly_mask()                                    # for negative-peak datasets
        >>> corrected = ssd.corrected_copy()                          # LPM with negative frames masked
        >>> corrected = ssd.corrected_copy(baseline=my_baseline)      # pre-computed XR baseline
        """
        start_time = time()
        ssd_copy = self.copy(trimmed=self.trimmed, trimming=self.trimming, datafiles=self.datafiles)

        if baseline is not None:
            import warnings
            warnings.warn(
                "Pre-computed baseline applies to XR only; "
                "UV baseline is computed normally.",
                stacklevel=2,
            )
            ssd_copy.xr.M -= baseline
        else:
            baseline = ssd_copy.xr.get_baseline2d(debug=debug, **baseline_kwargs)
            ssd_copy.xr.M -= baseline

        # Interpolate negative-peak frames: replace excluded columns with
        # per-row linear interpolation between the boundary values so that
        # the excluded region sits at the local baseline level instead of
        # being zeroed (which would conflict with the optimizer's own
        # baseline model).
        exclude = self._resolve_neg_peak_exclude(ssd_copy.xr)
        if exclude is not None and exclude.any():
            self._interpolate_excluded(ssd_copy.xr.M, exclude)

        if ssd_copy.uv is not None:
            baseline = ssd_copy.uv.get_baseline2d(debug=debug, **baseline_kwargs)
            ssd_copy.uv.M -= baseline

            # Interpolate UV frames corresponding to the XR negative-peak region
            if exclude is not None and exclude.any():
                mapping = self.get_mapping()
                if mapping is not None and not isinstance(mapping, tuple):
                    xr_jv = ssd_copy.xr.jv
                    uv_jv = ssd_copy.uv.jv
                    xr_frames_excluded = xr_jv[exclude]
                    uv_frames_mapped = mapping.slope * xr_frames_excluded + mapping.intercept
                    uv_lo, uv_hi = uv_frames_mapped.min(), uv_frames_mapped.max()
                    uv_exclude = (uv_jv >= uv_lo) & (uv_jv <= uv_hi)
                    if uv_exclude.any():
                        self._interpolate_excluded(ssd_copy.uv.M, uv_exclude)

        ssd_copy.time_required = time() - start_time
        ssd_copy.time_required_total = self.time_required_total + ssd_copy.time_required
        return ssd_copy

    @staticmethod
    def _resolve_neg_peak_exclude(xr):
        """Resolve anomaly mask into a bool exclude mask (or None)."""
        if not getattr(xr, 'has_anomaly_mask', False):
            return None
        np_mask = getattr(xr, 'anomaly_mask', None)
        jv = xr.jv
        if np_mask is None:
            return xr.get_recognition_curve().y < 0
        elif isinstance(np_mask, slice):
            i_start = np.searchsorted(jv, np_mask.start) if np_mask.start is not None else None
            i_stop  = np.searchsorted(jv, np_mask.stop, side='right') if np_mask.stop is not None else None
            exclude = np.zeros(len(jv), dtype=bool)
            exclude[slice(i_start, i_stop)] = True
            return exclude
        else:
            return np.asarray(np_mask, dtype=bool)

    @staticmethod
    def _interpolate_excluded(M, exclude):
        """Replace excluded columns with per-row linear interpolation.

        For each row of *M*, the excluded columns are replaced with values
        linearly interpolated between the last included column before the
        excluded region and the first included column after it.  If the
        excluded region touches an edge, the nearest included value is used
        (constant extrapolation).
        """
        idx = np.where(exclude)[0]
        if len(idx) == 0:
            return
        i_lo, i_hi = idx[0], idx[-1]
        n_cols = M.shape[1]
        # Boundary values for interpolation
        val_left = M[:, i_lo - 1] if i_lo > 0 else M[:, i_hi + 1] if i_hi + 1 < n_cols else np.zeros(M.shape[0])
        val_right = M[:, i_hi + 1] if i_hi + 1 < n_cols else val_left
        if i_lo == 0:
            val_left = val_right
        n_exc = i_hi - i_lo + 1
        for k, j in enumerate(range(i_lo, i_hi + 1)):
            t = (k + 1) / (n_exc + 1)
            M[:, j] = val_left * (1 - t) + val_right * t

    def estimate_mapping(self, debug=False):
        """ssd.estimate_mapping()
        Estimates the mapping information between UV and XR data.
        Parameters
        ----------
        debug : bool, optional
            If True, enables debug mode for more verbose output.
        Returns
        -------
        mapping : MappingInfo
            A MappingInfo object which contains the mapping information.
            If the mapping information is not available, returns None.
        """
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
            if self.uv is None:
                self.mapping = (1, 0)  # identity mapping for XR-only data
            else:
                self.estimate_mapping()
        return self.mapping

    def get_concfactor(self):
        """ssd.get_concfactor()
        Returns the concentration factor from the beamline information.

        Parameters
        ----------
        None

        Returns
        -------
        concfactor : float or None
            The concentration factor from the beamline information.
            If the beamline information is not available, returns None.
        """
        if self.beamline_info is None:
            return None
        else:
            return self.beamline_info.get_concfactor()
    
    def quick_decomposition(self, num_components=None, ranks=None, **kwargs):
        """ssd.quick_decomposition(num_components=None, proportions=None, xr_peakpositions=None, ranks=None, num_plates=None, **kwargs)

        Performs a quick decomposition of the SEC-SAXS data.

        See also: `Nontrivial Decomposition <https://biosaxs-dev.github.io/molass-tutorial/chapters/10/nontrivial.html>`_

        Three decomposition algorithms are available, selected by keyword:

        1. **Default** (no extra keywords) — greedy peak-recognition.
        2. **Proportional** (``proportions``) — area-ratio slicing.
        3. **Positioned** (``xr_peakpositions``) — peaks pinned to specified frame positions.

        ``proportions`` and ``xr_peakpositions`` are mutually exclusive.

        Parameters
        ----------
        num_components : int, optional
            Specifies the number of components which also implies the SVD rank
            used to denoise the matrix data.

        proportions : list of float, optional
            Specifies the approximate area ratios of the elution peaks.
            The values do not need to be normalized; for example,
            ``[1, 1]``, ``[0.5, 0.5]``, and ``[3, 3]`` all produce the same result
            because they are normalized internally.

            When this option is given, a **proportional decomposition** algorithm
            is used instead of the default peak-recognition algorithm.
            The proportional algorithm divides the total elution curve by cumulative area
            according to the given ratios, and fits an EGH model to each slice independently.
            This provides better initialization for cases with highly overlapping peaks,
            where the default algorithm may produce unstable results.

            The exact ratios do not need to be known precisely;
            even a rough estimate (e.g., ``[2, 1]`` when the true ratio is ``[1, 1]``)
            is usually sufficient.

        xr_peakpositions : list of float, optional
            Specifies the frame positions where peaks should be pinned.
            Uses a penalty-based optimizer (Nelder-Mead) that fits EGH peaks
            with a strong position constraint. ``num_components`` is inferred
            from the length if not provided.

            Mutually exclusive with ``proportions``.

        ranks : list of int, optional
            Specifies the ranks to be used for XR data.

        num_plates : int, optional
            Specifies the number of theoretical plates to be used for the optimization constraint.

        tau_limit : float, optional
            Maximum allowed ratio ``|tau| / sigma`` for positioned decomposition.
            Default 0.6.

        max_sigma : float, optional
            Maximum allowed Gaussian width (sigma) for positioned decomposition.
            Default 80.

        min_sigma : float, optional
            Minimum allowed Gaussian width (sigma) for positioned decomposition.
            Default 5.

        allow_negative_peaks : bool, optional
            If True, allow negative peak heights (H < 0) in the EGH model.
            This enables decomposition of components with negative scattering,
            such as those arising from buffer composition mismatch.
            Default False.

        debug : bool, optional
            If True, reload internal modules and show diagnostic plots.
            Default False.

        Returns
        -------
        decomposition : Decomposition
            A Decomposition object which contains the decomposition result.
        """
        
        debug = kwargs.get('debug', False)
        # Validate kwargs to catch typos early (issue #64)
        _KNOWN_KWARGS = {
            'proportions', 'xr_peakpositions', 'debug',
            'tau_limit', 'max_sigma', 'min_sigma', 'num_plates',
            'allow_negative_peaks',
            'ranks', 'randomize', 'seed', 'global_opt',
            'area_weight', 'sec_constraints', 'data_matrix', 'qv',
            'curve_model', 'smoothing', 'decompargs', 'peakpositions',
            'smooth_uv', 'consistent_uv', 'ip_effect_info',
        }
        unknown = set(kwargs) - _KNOWN_KWARGS
        if unknown:
            import warnings
            warnings.warn(
                f"quick_decomposition() received unrecognized keyword arguments: {unknown}. "
                f"Check for typos. Known kwargs: {sorted(_KNOWN_KWARGS)}",
                stacklevel=2,
            )
        if debug:
            import molass.LowRank.QuickImplement
            reload(molass.LowRank.QuickImplement)
        from molass.LowRank.QuickImplement import make_decomposition_impl

        # Guide users toward detect_peaks() when num_components is hardcoded
        proportions = kwargs.get('proportions', None)
        xr_peakpositions = kwargs.get('xr_peakpositions', None)
        if num_components is not None and proportions is None and xr_peakpositions is None:
            import logging
            logger = logging.getLogger(__name__)
            try:
                detected = self.xr.detect_peaks()
                if len(detected) != num_components:
                    logger.info(
                        "num_components=%d was specified, but detect_peaks() found %d peaks at %s. "
                        "Consider using xr_peakpositions=ssd.xr.detect_peaks() instead.",
                        num_components, len(detected), list(detected)
                    )
            except Exception:
                pass  # detect_peaks may fail on edge cases; don't block decomposition

        return make_decomposition_impl(self, num_components, **kwargs)

    def rigorous_decomposition(self, num_components=None, ranks=None, **kwargs):
        """ssd.rigorous_decomposition(num_components=None, proportions=None, ranks=None, num_plates=None, **kwargs)

        Performs a rigorous decomposition of the SEC-SAXS data.

        Parameters
        ----------
        num_components : int, optional
            Specifies the number of components which also implies the SVD rank
            used to denoise the matrix data.

        proportions : list of float, optional
            Specifies the proportions to be used for XR data.

        ranks : list of int, optional
            Specifies the ranks to be used for XR data.

        num_plates : int, optional
            Specifies the number of theoretical plates to be used for the optimization constraint.

        Returns
        -------
        decomposition : Decomposition
            A Decomposition object which contains the decomposition result.
        """
        
        debug = kwargs.get('debug', False)
        if debug:
            import molass.Rigorous.RigorousImplement
            reload(molass.Rigorous.RigorousImplement)
        from molass.Rigorous.RigorousImplement import make_rigorous_decomposition_impl

        return make_rigorous_decomposition_impl(self, num_components, **kwargs)

    def inspect_ip_effect(self, debug=False):
        """ssd.inspect_ip_effect()
        Inspects the inter-particle effect of the SEC-SAXS data.

        Parameters
        ----------
        debug : bool, optional
            If True, enables debug mode for more verbose output.

        Returns
        -------
        ip_effect_info : IpEffectInfo
            An IpEffectInfo object which contains the inspection result.
        """
        if debug:
            import molass.InterParticle.IpEffectInspect
            reload(molass.InterParticle.IpEffectInspect)
        from molass.InterParticle.IpEffectInspect import _inspect_ip_effect_impl
        return _inspect_ip_effect_impl(self, debug=debug)

    def get_uv_device_id(self):
        """ssd.get_uv_device_id()
        Returns the UV device ID from the beamline information.

        Parameters
        ----------
        None

        Returns
        -------
        uv_device_id : str or None
            The UV device ID from the beamline information.
            If the beamline information is not available, returns None.
        """
        if self.beamline_info is None:
            return None
        else:
            return self.beamline_info.uv_device_id

    def get_beamline_name(self):
        """ssd.get_beamline_name()
        Returns the beamline name from the beamline information.

        Parameters
        ----------
        None

        Returns
        -------
        beamline_name : str or None
            The beamline name from the beamline information.
            If the beamline information is not available, returns None.
        """
        if self.beamline_info is None:
            return None
        else:
            return self.beamline_info.name

    def get_data_info(self):
        """ssd.get_data_info()

        Returns a machine-readable summary of the dataset characteristics.
        Useful for automated diagnostics: an AI agent can call this to understand
        the data without reading plots.

        Returns
        -------
        info : DataInfo (namedtuple)
            A namedtuple with the following fields:

            - ``n_xr_frames`` (int or None): Number of XR frames
            - ``n_uv_frames`` (int or None): Number of UV frames
            - ``uv_peak_wavelength`` (float or None): Wavelength (nm) of max absorbance at the XR peak frame
            - ``uv_pickat`` (float or None): Current UV pickat setting (default 280 nm)
            - ``uv_monitor`` (float or None): Alias for ``uv_pickat`` (monitoring wavelength)
            - ``xr_peak_frame`` (int or None): Frame index of the XR elution peak
            - ``is_trimmed`` (bool): Whether the data has been trimmed
            - ``pickat_mismatch`` (bool): True if uv_peak_wavelength differs from uv_pickat by >5 nm
            - ``has_negative_xr_regions`` (bool): True if anomalous frames are detected
              (Tier 1: column-sum neg_depth > 3%, OR Tier 2: baseline self-test p < 0.01),
              indicating that ``set_anomaly_mask()`` should be called
            - ``negative_xr_fraction`` (float or None): Fraction of XR frames with negative recognition-curve values
            - ``baseline_selftest_p`` (float or None): p-value from the baseline self-test
              (Wilcoxon signed-rank). Low values (< 0.01) indicate buffer-frame contamination.
              None if XR data is absent.

        Examples
        --------
        >>> info = ssd.get_data_info()
        >>> print(info)
        >>> if info.pickat_mismatch:
        ...     print(f"Consider using uv_monitor={info.uv_peak_wavelength:.0f}")
        >>> if info.has_negative_xr_regions:
        ...     print("Call ssd.set_anomaly_mask() before corrected_copy()")
        """
        from collections import namedtuple
        DataInfo = namedtuple('DataInfo', [
            'n_xr_frames', 'n_uv_frames',
            'uv_peak_wavelength', 'uv_pickat', 'uv_monitor',
            'xr_peak_frame', 'is_trimmed', 'pickat_mismatch',
            'has_negative_xr_regions', 'negative_xr_fraction',
            'baseline_selftest_p',
        ])

        n_xr_frames = self.xr.M.shape[1] if self.xr is not None else None
        n_uv_frames = self.uv.M.shape[1] if self.uv is not None else None

        xr_peak_frame = None
        uv_peak_wl = None
        uv_pickat = None
        pickat_mismatch = False
        has_negative_xr = False
        negative_xr_frac = None
        selftest_p = None

        if self.xr is not None:
            xr_icurve = self.xr.get_recognition_curve()
            xr_peak_frame = int(xr_icurve.x[np.argmax(xr_icurve.y)])
            # Anomaly detection: use matrix column-sum (sum over all q-rows).
            # The single-row icurve has noise-level negatives in all datasets;
            # the full-sum amplifies real anomalous dips above noise.
            xr_colsum = self.xr.M.sum(axis=0)
            neg_depth = abs(xr_colsum.min()) / xr_colsum.max() if xr_colsum.max() > 0 else 0
            negative_xr_frac = float(np.mean(xr_colsum < 0))
            has_negative_xr = neg_depth > 0.03  # Tier 1: dip >3% of peak height

            # Tier 2: baseline self-test (catches subtle cases like ATP).
            # Compare per-q-row negative fraction in peak region:
            # buffer-mean-flat baseline vs endpoint-linear baseline.
            # If using buffer info makes things worse, buffer frames are contaminated.
            selftest_p = _baseline_selftest(self.xr.M, xr_icurve)
            if not has_negative_xr and selftest_p is not None:
                has_negative_xr = selftest_p < 0.01

        if self.uv is not None:
            uv_pickat = self.uv.pickat
            # Find the wavelength of max absorbance at the XR peak frame
            if xr_peak_frame is not None:
                mapping = self.get_mapping()
                uv_icurve = mapping.uv_curve
                uv_frame = mapping.get_mapped_index(
                    xr_peak_frame, xr_icurve.x, uv_icurve.x)
                spectrum = self.uv.M[:, uv_frame]
                uv_peak_wl = float(self.uv.wavelengths[np.argmax(spectrum)])
            else:
                # No XR data; use UV peak frame directly
                uv_elution = self.uv.M.sum(axis=0)
                uv_peak_frame = np.argmax(uv_elution)
                spectrum = self.uv.M[:, uv_peak_frame]
                uv_peak_wl = float(self.uv.wavelengths[np.argmax(spectrum)])

            if uv_peak_wl is not None and uv_pickat is not None:
                # Only flag mismatch when absorbance peak is ABOVE pickat wavelength.
                # Peak below pickat (e.g., 230 nm peptide bond vs 280 nm pickat) is normal for proteins.
                # Peak above pickat (e.g., 290 nm nucleotide vs 280 nm) signals a non-standard sample.
                pickat_mismatch = (uv_peak_wl - uv_pickat) > 5

        return DataInfo(
            n_xr_frames=n_xr_frames,
            n_uv_frames=n_uv_frames,
            uv_peak_wavelength=uv_peak_wl,
            uv_pickat=uv_pickat,
            uv_monitor=uv_pickat,
            xr_peak_frame=xr_peak_frame,
            is_trimmed=self.trimmed,
            pickat_mismatch=pickat_mismatch,
            has_negative_xr_regions=has_negative_xr,
            negative_xr_fraction=negative_xr_frac,
            baseline_selftest_p=selftest_p,
        )

    def export(self, folder, prefix=None, fmt='%.18e', xr_only=False, uv_only=False):
        """ssd.export(folder, prefix=None, fmt='%.18e', xr_only=False, uv_only=Fals)

        Exports the data to a file.

        Parameters
        ----------
        folder : str
            Specifies the folder path where the data will be exported.

        prefix : str, optional
            Specifies the filename prefix to be used for the exported data.
            If it is None, "PREFIX_" will be used.

        fmt : str, optional
            Specifies the format to be used for the exported data.
            The default is '%.18e'.

        xr_only : bool, optional
            If True, only export XR data.

        uv_only : bool, optional
            If True, only export UV data.            

        Returns
        -------
        filepath : str
            The full path of the exported file.
        """
        from molass.DataUtils.ExportSsd import export_ssd_impl
        uv_device_id = self.get_uv_device_id()
        return export_ssd_impl(self, folder=folder, prefix=prefix, fmt=fmt, uv_device_id=uv_device_id, xr_only=xr_only, uv_only=uv_only)
    
    def plot_varied_decompositions(self, proportions, rgcurve=None, best=None, debug=False):
        """ssd.plot_varied_decompositions(proportions, **kwargs)

        Plots a set of varied decompositions.

        Parameters
        ----------
        proportions : list of float
            A list of proportions to be used for the varied decompositions.

        rgcurve : object, optional
            A reference to the RG curve to be used for the plot.

        best : int, optional
            number of best results to be highlighted.

        debug : bool, optional
            If True, enables debug mode.

        Returns
        -------
        result : PlotResult
            A PlotResult object which contains the following attributes.

            fig: Figure
            axes: Axes
        """
        if debug:
            import molass.Decompose.VaryUtils
            reload(molass.Decompose.VaryUtils)
        from molass.Decompose.VaryUtils import _plot_varied_decompositions_impl
        xr_icurve = self.xr.get_icurve()
        return _plot_varied_decompositions_impl(xr_icurve, proportions, rgcurve=rgcurve, best=best, debug=debug)
    
    def get_spectral_vectors(self):
        """ssd.get_spectral_vectors()
        Returns the spectral vectors for XR and UV data.

        Parameters
        ----------
        None

        Returns
        -------
        spectral_vectors : list of np.ndarray
            A list of two numpy arrays which contain the spectral vectors for XR and UV data.
        """
        if self.uv is None:
            # temporary work-around for the case without UV data
            return [self.xr.qv, self.xr.qv]
        else:
            return [self.xr.qv, self.uv.wv]