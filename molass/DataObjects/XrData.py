"""
    DataObjects.XrData.py
"""
import numpy as np
from importlib import reload
from molass.DataObjects.SsMatrixData import SsMatrixData
from molass.DataObjects.Curve import Curve

PICKAT = 0.02   # default value for pickat

class XrData(SsMatrixData):
    """
    XrData class for XR matrix data. 
    Inherits from SsMatrixData and adds XR-specific functionality.

    Attributes
    ----------
    qv : array-like
        The q-values corresponding to the angular axis.
    baseline_method : str
        Default is ``'linear'``.
        Can be overridden by passing ``baseline_method=...`` to the constructor.
    """
    def __init__(self, M, iv, jv, E=None, **kwargs):
        """Initialize the XrData object.

        Parameters
        ----------
        M : 2D array-like, shape (len(iv), len(jv))
            The 2D matrix of intensity values.
        iv : array-like
            The q-values corresponding to the angular (row) axis.
        jv : array-like or None
            The values corresponding to the temporal (column) axis.
        E : 2D array-like or None, optional
            The 2D matrix of error values. Default None.
        kwargs : dict, optional
            Additional keyword arguments to pass to the SsMatrixData constructor.
        """
        kwargs.setdefault('baseline_method', 'linear')
        super().__init__(M, iv, jv, E, **kwargs)
        self.qv = iv
        self.pickat = PICKAT

    @property
    def xr_pickat(self):
        """Alias for ``pickat`` — the default q-value for i-curve extraction."""
        return self.pickat

    @xr_pickat.setter
    def xr_pickat(self, value):
        self.pickat = value

    def copy(self, slices=None):
        result = super().copy(slices=slices)
        result.pickat = self.pickat
        return result

    def get_ipickvalue(self):
        """Get the default pickvalue for i-curves.
        Returns
        -------
        float
            The default pickvalue for i-curves.
        """
        return self.pickat

    def get_icurve(self, pickat=None):
        """xr.get_icurve(pickat=0.02)
        
        Returns an i-curve from the XR matrix data.

        Parameters
        ----------
        pickat : float, optional
            Specifies the value in ssd.qv where to pick an i-curve.
            The i-curve will be made from self.M[i,:] where
            the picking index i will be determined to satisfy
                self.qv[i-1] <= pickat < self.qv[i]
            according to bisect_right.
            If None, uses self.pickat (default 0.02, or the value set
            via SSD(xr_pickat=...)).
        
        Returns
        -------
        Curve
            The extracted i-curve.

        Examples
        --------
        >>> curve = xr.get_icurve()

        >>> curve = xr.get_icurve(pickat=0.02)
        """
        if pickat is None:
            pickat = self.pickat
        return super().get_icurve(pickat)

    def get_recognition_curve(self):
        """xr.get_recognition_curve()

        Return the elution curve used for peak detection and buffer-frame
        classification, honouring the ``'elution_recognition'`` global option.

        - ``'icurve'`` (default) — single row at q\u22480.02, same as
          :meth:`get_icurve`.  High S/N in the Guinier regime; preserves
          the existing behaviour unchanged.
        - ``'sum'`` — sum of the (already-trimmed) matrix over all q-rows.
          Exposes q-dependent baseline drift that is invisible at q\u22480.02
          (e.g. MY-type datasets).

        Returns
        -------
        Curve
            The recognition elution curve.

        Examples
        --------
        >>> from molass import set_molass_options
        >>> set_molass_options(elution_recognition='sum')
        >>> curve = xr.get_recognition_curve()   # now returns M.sum(axis=0)
        >>> set_molass_options(elution_recognition='icurve')  # restore default
        """
        from molass.Global.Options import get_molass_options
        mode = get_molass_options('elution_recognition')
        if mode == 'icurve':
            return self.get_icurve()
        else:  # 'sum'
            from molass.DataObjects.Curve import Curve
            return Curve(self.jv, self.M.sum(axis=0))

    def get_usable_qrange(self, **kwargs):
        """xr.get_usable_qrange()
        
        Returns a pair of indeces which should be used
        as a slice for the angular axis to trim away
        unusable XR data regions. 

        Parameters
        ----------
        None

        Returns
        -------
        (int, int)
            A pair of indeces (i_start, i_end) to be used as a slice for the angular axis.

        Examples
        --------
        >>> i, j = xr.get_usable_qrange()
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.Trimming.UsableQrange
            reload(molass.Trimming.UsableQrange)
        from molass.Trimming.UsableQrange import get_usable_qrange_impl
        return get_usable_qrange_impl(self, **kwargs)

    def get_ibaseline(self, pickat=None, method=None, **kwargs):
        """xr.get_ibaseline()
        
        Returns a baseline i-curve from the XR matrix data.

        Parameters
        ----------
        pickat : float, optional
            q-value at which to pick the i-curve for baseline fitting.
            If None, uses self.pickat (default 0.02, or the value set
            via SSD(xr_pickat=...)).

        method : str, optional
            The baseline method to be used. If None, the method set in the object will be
            used.
        kwargs : dict, optional
            Additional keyword arguments to pass to the baseline computation function.
            These will be merged with the default_kwargs defined above.
        debug : bool, optional
            If True, enable debug mode.
            
        Returns
        -------
        baseline: Curve
            The computed baseline i-curve.
            This curve can be subtracted from the original i-curve to obtain a background-subtracted curve.

        Examples
        --------
        >>> curve = xr.get_icurve()
        >>> baseline = xr.get_ibaseline()
        >>> corrected_curve = curve - baseline
        """
        debug = kwargs.get('debug', False)
        if debug:
            import molass.Baseline.BaselineUtils
            reload(molass.Baseline.BaselineUtils)
        from molass.Baseline.BaselineUtils import get_xr_baseline_func
        icurve = self.get_icurve(pickat=pickat)
        if method is None:
            method = self.get_baseline_method()
        compute_baseline_impl = get_xr_baseline_func(method)
        kwargs['moment'] = self.get_moment()
        y = compute_baseline_impl(icurve.x, icurve.y, **kwargs)
        return Curve(icurve.x, y, type='i')

    def compute_rgcurve(self, return_info=False, debug=False):
        """ssd.compute_rgcurve()

        Returns a Rg-curve which is computed using the Molass standard method.

        Parameters
        ----------
        None

        Returns
        -------
        An :class:`~molass.Guinier.RgCurve` object.
        """
        if debug:
            
            import molass.Guinier.RgCurveUtils
            reload(molass.Guinier.RgCurveUtils)
        from molass.Guinier.RgCurveUtils import compute_rgcurve_info
        rginfo = compute_rgcurve_info(self)
        if return_info:
            return rginfo
        else:
            if debug:
                import molass.Guinier.RgCurve
            from molass.Guinier.RgCurve import construct_rgcurve_from_list
            return construct_rgcurve_from_list(rginfo)

    def compute_rgcurve_atsas(self, return_info=False, debug=False):
        """ssd.compute_rgcurve_atsas()

        Returns an Rg-curve which is computed using the ATSAS `autorg <https://www.embl-hamburg.de/biosaxs/manuals/autorg.html>`_.

        Parameters
        ----------
        None

        Returns
        -------
        An :class:`~molass.Guinier.RgCurve` object.
        """
        if debug:
            import molass.Guinier.RgCurveUtils
            reload(molass.Guinier.RgCurveUtils)
        from molass.Guinier.RgCurveUtils import compute_rgcurve_info_atsas
        rginfo = compute_rgcurve_info_atsas(self)
        if return_info:
            return rginfo
        else:
            if debug:
                import molass.Guinier.RgCurve
                reload(molass.Guinier.RgCurve)
            from molass.Guinier.RgCurve import construct_rgcurve_from_list
            return construct_rgcurve_from_list(rginfo, result_type='atsas')

    def detect_peaks(self, prominence=0.005, distance=20, window_length=31,
                     polyorder=3, return_properties=False):
        """xr.detect_peaks()

        Detect peaks in the total XR elution curve using Savitzky-Golay
        smoothing followed by scipy ``find_peaks``.

        The returned list can be passed directly to
        ``ssd.quick_decomposition(xr_peakpositions=peaks)``.

        Parameters
        ----------
        prominence : float, optional
            Minimum prominence as a fraction of the smoothed curve maximum.
            Default 0.005 (0.5 %).
        distance : int, optional
            Minimum number of frames between adjacent peaks. Default 20.
        window_length : int, optional
            Savitzky-Golay filter window length (must be odd). Default 31.
        polyorder : int, optional
            Savitzky-Golay filter polynomial order. Default 3.
        return_properties : bool, optional
            If True, return a tuple ``(peaks, properties)`` where
            *properties* is a dict containing ``'prominences'`` and
            ``'peak_heights'`` arrays.  Default False (backward-compatible).

        Returns
        -------
        list of int
            Frame numbers of detected peaks, sorted by frame number.
            Returned alone when ``return_properties=False``.
        tuple of (list of int, dict)
            ``(peaks, properties)`` when ``return_properties=True``.

        Examples
        --------
        >>> peaks = ssd.xr.detect_peaks()
        >>> decomp = ssd.quick_decomposition(xr_peakpositions=peaks)

        >>> peaks, props = ssd.xr.detect_peaks(return_properties=True)
        >>> props['prominences']   # array of peak prominences
        """
        from scipy.signal import savgol_filter, find_peaks
        frames = self.jv
        total_elution = self.get_recognition_curve().y
        wl = min(window_length, len(total_elution))
        if wl % 2 == 0:
            wl -= 1
        if wl < polyorder + 2:
            smooth = total_elution
        else:
            smooth = savgol_filter(total_elution, window_length=wl, polyorder=polyorder)
        peaks_idx, props = find_peaks(smooth, prominence=smooth.max() * prominence, distance=distance)
        peak_frames = [int(frames[i]) for i in peaks_idx]
        if return_properties:
            out_props = {
                'prominences': props['prominences'],
                'peak_heights': smooth[peaks_idx],
            }
            return peak_frames, out_props
        return peak_frames

    def plot_peaks(self, ax=None, prominence=0.005, distance=20,
                   window_length=31, polyorder=3):
        """xr.plot_peaks()

        Visualize detected peaks on the total XR elution curve.

        Parameters
        ----------
        ax : matplotlib Axes, optional
            If provided, plot on this axes.  Otherwise create a new figure.
        prominence, distance, window_length, polyorder :
            Forwarded to :meth:`detect_peaks`.

        Returns
        -------
        tuple of (Figure, Axes)
        """
        import matplotlib.pyplot as plt

        peaks, props = self.detect_peaks(
            prominence=prominence, distance=distance,
            window_length=window_length, polyorder=polyorder,
            return_properties=True,
        )

        frames = self.jv
        total_elution = self.M.sum(axis=0)
        wl = min(window_length, len(total_elution))
        if wl % 2 == 0:
            wl -= 1
        if wl < polyorder + 2:
            smooth = total_elution
        else:
            from scipy.signal import savgol_filter
            smooth = savgol_filter(total_elution, window_length=wl, polyorder=polyorder)

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 4))
        else:
            fig = ax.get_figure()

        import numpy as np
        ax.plot(frames, total_elution, 'gray', alpha=0.4, label='raw elution')
        ax.plot(frames, smooth, 'b-', lw=1.5, label='smoothed')
        for i, pk in enumerate(peaks):
            prom = props['prominences'][i]
            idx = np.searchsorted(frames, pk)
            ax.axvline(pk, color='red', ls=':', alpha=0.7)
            ax.annotate(f'{pk}\n(prom={prom:.2f})',
                        (pk, smooth[min(idx, len(smooth) - 1)]),
                        textcoords='offset points', xytext=(5, 10),
                        fontsize=7, color='red')
        ax.set_xlabel('Frame')
        ax.set_ylabel('Total XR intensity')
        ax.set_title(f'detect_peaks(): {len(peaks)} peaks found')
        ax.legend()
        # Add headroom so annotations on the tallest peak don't overlap the title
        ylo, yhi = ax.get_ylim()
        ax.set_ylim(ylo, yhi + (yhi - ylo) * 0.15)
        # Brief explanation of "prominence"
        ax.text(0.01, 0.97,
                'prominence = how much a peak\n'
                'stands out above the deeper of\n'
                'the two valleys on either side',
                transform=ax.transAxes, fontsize=6.5,
                verticalalignment='top', color='gray',
                fontstyle='italic')
        fig.tight_layout()
        return fig, ax

    def get_jcurve_array(self, j=None, peak=None):
        """xr.get_jcurve_array(j=None, peak=None)

        Returns the j-curve array.
        This method extracts the q, I, and sigq values from the XR data.
        It uses the first peak in the i-curve to determine the j-curve.
        
        Parameters
        ----------
        j : int, optional
            The index of the j-curve to use. If None, the peak argument is used.

        peak : int, optional
            This argument is used only if j is None.
            The index of the peak in the i-curve to use. If None, the first peak is used.            

        Returns
        -------
        jcurve_array : np.ndarray
        """
        from molass.DataObjects.Curve import create_jcurve

        q = self.qv
        if j is None:
            icurve = self.get_icurve()
            peaks = icurve.get_peaks()
            if peak is None:
                peak = 0
            j = peaks[peak]
                
        I = self.get_jcurve(j).y
        sigq = create_jcurve(q, self.E, j).y
        return np.array([q, I, sigq]).T