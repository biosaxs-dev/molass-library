"""
    DataObjects.SsMatrixData.py
"""
import numpy as np
from molass.DataObjects.Curve import create_icurve, create_jcurve

class SsMatrixData:
    """A class to represent a SAXS/UV matrix data object.
    It contains a 2D matrix M where M[i,j] is the intensity value
    at the i-th value of the first variable (iv) and the j-th value
    of the second variable (jv).
    
    Attributes
    ----------
    iv : array-like
        The values of the first variable (e.g., scattering angle or q).
    jv : array-like
        The values of the second variable (e.g., time or wavelength).
    M : 2D array-like
        The 2D matrix of intensity values.
    data : 2D array-like (property)
        Human-readable alias for ``M`` — the core intensity matrix.
    E : 2D array-like or None
        The 2D matrix of error values. It can be None if errors are not available
    moment : Moment or None
        The moment of the data along the iv axis. It can be None if not computed.
    baseline_method : str
        The method used for baseline correction. Default is 'linear'.
    allow_negative_peaks : bool
        Deprecated alias for ``has_anomaly_mask``.
    has_anomaly_mask : bool
        If True, frames in the anomaly region are excluded from LPM's
        anchor pool before baseline fitting, preventing contamination from
        physically anomalous frames (e.g. negative-peak regions).
        Default False.
    negative_peak_mask : array-like of bool, slice, or None
        Deprecated alias for ``anomaly_mask``.
    anomaly_mask : array-like of bool, slice, or None
        Explicit mask of frames to exclude from LPM fitting when
        ``has_anomaly_mask=True``.  If None (default), the mask is
        derived automatically from the recognition curve (frames where y < 0).
    """
    def __init__(self, M, iv, jv, E=None,
                 moment=None,
                 baseline_method='linear',
                 allow_negative_peaks=False,
                 negative_peak_mask=None):
        """Initialize the SsMatrixData object.

        Parameters
        ----------
        M : 2D array-like, shape (len(iv), len(jv))
            The 2D intensity matrix.  Row axis = iv, column axis = jv.
        iv : array-like
            Row-axis values (e.g. q-values for XR, wavelengths for UV).
        jv : array-like or None
            Column-axis values (frame numbers).  If None, defaults to
            ``np.arange(M.shape[1])``.
        E : 2D array-like or None, optional
            Error matrix with the same shape as M.  Default None.
        """
        self.M = M
        self.iv = iv
        if jv is None:
            jv = np.arange(M.shape[1])
        self.jv = jv
        self.E = E      # may be None
        self.moment = moment
        self.baseline_method = baseline_method
        self.has_anomaly_mask = allow_negative_peaks
        self.anomaly_mask = negative_peak_mask  # None = auto-detect from recognition curve

    @property
    def data(self):
        """The 2D intensity matrix (alias for ``M``, following numpy/pandas/xarray convention)."""
        return self.M

    @property
    def q_values(self):
        """Row-axis values (alias for ``iv``), typically scattering vector q."""
        return self.iv

    @q_values.setter
    def q_values(self, value):
        self.iv = value

    @property
    def frame_indices(self):
        """Column-axis values (alias for ``jv``), typically frame numbers."""
        return self.jv

    @frame_indices.setter
    def frame_indices(self, value):
        self.jv = value

    def __repr__(self):
        return (
            f"{self.__class__.__name__}: M shape (iv={len(self.iv)}, jv={len(self.jv)})"
        )

    def copy(self, slices=None):
        """Return a copy of the SsMatrixData object.

        Parameters
        ----------
        slices : tuple of slices, optional
            The slices to apply to the iv, jv, and M attributes.
        """
        if slices is None:
            islice = slice(None, None)
            jslice = slice(None, None)
        else:
            islice, jslice = slices
        Ecopy = None if self.E is None else self.E[islice,jslice].copy()
        return self.__class__(  # __class__ is used to ensure that the correct subclass is instantiated
                            self.M[islice,jslice].copy(),
                            self.iv[islice].copy(),
                            self.jv[jslice].copy(),
                            Ecopy,
                            moment=None,  # note that moment is not copied
                            baseline_method=self.baseline_method,
                            allow_negative_peaks=self.has_anomaly_mask,
                            negative_peak_mask=self.anomaly_mask,
                            )

    def get_icurve(self, pickat):
        """md.get_icurve(pickat)
        get an i-curve from the matrix data.
        
        Parameters
        ----------
        pickat : float
            Specifies the value to pick an i-curve.
            The i-curve will be made from ssd.M[i,:] where ssd.iv[i] is the largest value
            that is less than or equal to pickat.

        Examples
        --------
        >>> curve = md.get_icurve(0.1)
        """
        return create_icurve(self.jv, self.M, self.iv, pickat)
    
    def get_jcurve(self, j):
        """md.get_jcurve(j)

        Returns a j-curve from the matrix data.

        Parameters
        ----------
        j : int
            Specifies the index to pick a j-curve.
            The j-curve will be made from ssd.xrM[:,j].
            
        Examples
        --------
        >>> curve = md.get_jcurve(150)
        """
        return create_jcurve(self.iv, self.M, j)

    def get_recognition_curve(self):
        """md.get_recognition_curve()

        Return the elution curve used for peak detection and buffer-frame
        classification.  The base implementation always returns the sum over
        all rows (``M.sum(axis=0)``).  :class:`XrData` overrides this to
        honour the ``'elution_recognition'`` global option.

        Returns
        -------
        Curve
            The recognition elution curve.
        """
        from molass.DataObjects.Curve import Curve
        return Curve(self.jv, self.M.sum(axis=0))

    def get_moment(self):
        """Get the moment of the matrix data along the iv axis.

        Returns
        -------
        moment: EghMoment
            The moment object representing the moment along the iv axis.
        """
        if self.moment is None:
            from molass.Stats.EghMoment import EghMoment
            icurve = self.get_icurve()
            self.moment = EghMoment(icurve)
        return self.moment

    def set_baseline_method(self, method):
        """Set the baseline method for this data object."""
        self.baseline_method = method

    def get_baseline_method(self):
        """Get the baseline method for this data object."""
        return self.baseline_method

    def set_anomaly_mask(self, mask=None):
        """Declare that this dataset contains anomalous frames to exclude from baseline fitting.

        When set, ``get_baseline2d()`` excludes the specified frames from
        LPM's anchor pool before baseline fitting.  LPM itself is unchanged;
        only the frame set it operates on is filtered.

        Parameters
        ----------
        mask : array-like of bool, slice, or None, optional
            Explicit mask of frames to exclude (True = exclude).  If None
            (default), the mask is derived automatically at fitting time from
            the recognition curve (frames where y < 0).  Use a manual mask
            when the anomalous region is known from domain knowledge
            (e.g. ``mask=slice(1200, 1350)``).  When a ``slice`` is given,
            start and stop are interpreted as **frame numbers** (values in
            ``jv``), not array indices.

        Notes
        -----
        Both ``has_anomaly_mask`` and ``anomaly_mask`` are
        propagated by ``copy()`` and ``corrected_copy()``, so the typical
        workflow is::

            ssd.set_anomaly_mask()            # auto-detect
            # or:
            ssd.set_anomaly_mask(mask=slice(1200, 1350))  # manual
            corrected = ssd.corrected_copy()  # mask applied automatically
        """
        self.has_anomaly_mask = True
        self.anomaly_mask = mask

    def set_allow_negative_peaks(self, value=True, mask=None):
        """Deprecated: use ``set_anomaly_mask(mask)`` instead.

        When *value* is True, delegates to ``set_anomaly_mask(mask)``.
        When *value* is False, clears the anomaly mask.
        """
        import warnings
        warnings.warn(
            "set_allow_negative_peaks() is deprecated; use set_anomaly_mask(mask) instead.",
            DeprecationWarning, stacklevel=2,
        )
        if value:
            self.set_anomaly_mask(mask=mask)
        else:
            self.has_anomaly_mask = False
            self.anomaly_mask = None

    @property
    def allow_negative_peaks(self):
        """Deprecated alias for ``has_anomaly_mask``."""
        return self.has_anomaly_mask

    @allow_negative_peaks.setter
    def allow_negative_peaks(self, value):
        self.has_anomaly_mask = value

    @property
    def negative_peak_mask(self):
        """Deprecated alias for ``anomaly_mask``."""
        return self.anomaly_mask

    @negative_peak_mask.setter
    def negative_peak_mask(self, value):
        self.anomaly_mask = value

    def get_baseline2d(self, **kwargs):
        """Get the 2D baseline for the matrix data using the specified method.

        Parameters
        ----------
        method : str, optional
            Baseline method to use. If given, overrides the instance's
            ``baseline_method`` for this call only. Valid values are
            ``'buffit'``, ``'linear'``, ``'uvdiff'``, ``'integral'``.
        endpoint_fraction : float, optional
            Only used when ``method='linear'``.  If given and > 0, switches
            the LPM anchor from the bottom-25th-percentile frames to the
            leading and trailing ``k = max(2, int(endpoint_fraction * n))``
            frames.  Only valid for "easy" datasets where the run starts and
            ends in clean buffer.  **Not** the recommended approach for
            negative-peak datasets — use ``set_anomaly_mask()``
            instead.  Default ``None`` — standard LPM unchanged.
        method_kwargs : dict, optional
            Additional keyword arguments to pass to the baseline fitting method.
        debug : bool, optional
            If True, enable debug mode.
            
        Returns
        -------
        baseline : ndarray
            The 2D baseline array with the same shape as self.M.

        Examples
        --------
        >>> bl = xr.get_baseline2d()                        # standard LPM
        >>> bl = xr.get_baseline2d(endpoint_fraction=0.15)  # endpoint-anchored (easy datasets only)
        >>> xr.set_anomaly_mask()                   # auto-detect negative frames, mask from LPM
        >>> bl = xr.get_baseline2d()                        # LPM with anomalous frames excluded
        >>> xr.set_anomaly_mask(mask=slice(1200, 1350))  # manual region known from observation
        """
        from molass.Baseline import Baseline2D
        debug = kwargs.get('debug', False)
        counter = [0, 0, 0] if debug else None
        method = kwargs.get('method', self.baseline_method)
        if method in ['linear', 'uvdiff', 'integral']:
            import io, contextlib
            from molass_legacy.SerialAnalyzer.ElutionBaseCurve import ElutionBaseCurve as _EBC
            with contextlib.redirect_stdout(io.StringIO()):
                _ecurve = _EBC(self.get_recognition_curve().y)
                _size_sigma = _ecurve.compute_size_sigma()
            default_kwargs = dict(jv=self.jv, ssmatrix=self, counter=counter, size_sigma=_size_sigma)
            endpoint_fraction = kwargs.get('endpoint_fraction', None)
            if endpoint_fraction is not None:
                default_kwargs['endpoint_fraction'] = endpoint_fraction
            elif self.has_anomaly_mask:
                # Derive exclude mask: frames to remove from LPM's anchor pool.
                # Use stored mask if provided, else auto-detect from recognition curve.
                np_mask = self.anomaly_mask
                if np_mask is None:
                    # Auto-detect: frames where the recognition curve is negative
                    rc_y = self.get_recognition_curve().y
                    exclude = rc_y < 0
                elif isinstance(np_mask, slice):
                    # Interpret start/stop as frame numbers (jv values),
                    # not array indices.  Convert via searchsorted.
                    jv = self.jv
                    i_start = np.searchsorted(jv, np_mask.start) if np_mask.start is not None else None
                    i_stop  = np.searchsorted(jv, np_mask.stop, side='right') if np_mask.stop is not None else None
                    exclude = np.zeros(len(jv), dtype=bool)
                    exclude[slice(i_start, i_stop)] = True
                else:
                    exclude = np.asarray(np_mask, dtype=bool)
                include = ~exclude
                if include.any():
                    default_kwargs['mask'] = include
            if method == 'uvdiff':
                from molass.Baseline.UvdiffBaseline import get_uvdiff_baseline_info
                default_kwargs['uvdiff_info'] = get_uvdiff_baseline_info(self)
        elif method == 'buffit':
            from molass.Baseline.BuffitBaseline import _otsu_threshold
            _elution_sum = self.get_recognition_curve().y
            _elution_norm = _elution_sum / _elution_sum.max()
            _threshold = kwargs.get('threshold', None)
            if _threshold is None:
                _threshold = _otsu_threshold(_elution_norm)   # adaptive (Otsu)
            _buffer_mask = _elution_norm < _threshold
            default_kwargs = dict(jv=self.jv, buffer_mask=_buffer_mask)
        else:
            default_kwargs = {}
        method_kwargs = kwargs.get('method_kwargs', default_kwargs)
        baseline_fitter = Baseline2D(self.jv, self.iv)
        baseline, params_not_used = baseline_fitter.individual_axes(
            self.M.T, axes=0, method=method, method_kwargs=method_kwargs
        )
        if debug:
            if counter is not None:
                print(f"Baseline fitting completed with {counter} iterations.")  
        return baseline.T

    def get_snr_weights(self):
        """Per-q-row signal-to-noise ratio weights.

        Returns
        -------
        weights : ndarray, shape (n_q,)
            w_i = mean(I_i) / sigma_noise_i, clipped to >= 0.
        """
        mean_I = np.mean(self.M, axis=1)
        if self.E is not None:
            sigma = np.mean(self.E, axis=1)
            sigma = np.maximum(sigma, 1e-30)
        else:
            sigma = np.std(np.diff(self.M.astype(float), axis=1), axis=1) / np.sqrt(2)
            sigma = np.maximum(sigma, 1e-30)
        return np.maximum(mean_I / sigma, 0)

    def get_positive_ratio(self, baseline=None, weighting='snr'):
        """Fraction of non-negative residual elements, optionally SNR-weighted.

        Parameters
        ----------
        baseline : ndarray or None
            2D baseline array with the same shape as self.M.
            If ``None`` (default), the data is assumed already corrected
            and a zero baseline is used.
        weighting : {'snr', 'uniform'}
            'snr' (default) weights each q-row by its SNR so that
            informative low-q rows dominate over noisy high-q rows.

        Returns
        -------
        positive_ratio : float
        """
        if baseline is None:
            baseline = np.zeros_like(self.M)
        residual = self.M - baseline
        per_row = np.mean(residual >= 0, axis=1)
        if weighting == 'uniform':
            return float(np.mean(per_row))
        weights = self.get_snr_weights()
        if weights.sum() == 0:
            return float(np.mean(per_row))
        return float(np.average(per_row, weights=weights))

    def get_bpo_ideal(self, weighting='snr'):
        """Get the dataset-relative ideal positive_ratio for baseline evaluation.

        With ``weighting='snr'`` (default), computes per-q-row noisiness,
        looks up per-row ideal from the BPO table, and aggregates with SNR
        weights.  With ``weighting='uniform'``, uses the original single
        global noisiness.

        Parameters
        ----------
        weighting : {'snr', 'uniform'}

        Returns
        -------
        bpo_ideal : float
            The expected positive_ratio in [0, 1].
        """
        import io, contextlib
        from molass_legacy.SerialAnalyzer.ElutionBaseCurve import ElutionBaseCurve as _EBC
        from molass_legacy.SerialAnalyzer.BasePercentileOffset import base_percentile_offset
        from scipy.interpolate import LSQUnivariateSpline

        with contextlib.redirect_stdout(io.StringIO()):
            _ecurve = _EBC(self.get_recognition_curve().y.astype(float))
            _size_sigma = _ecurve.compute_size_sigma()

        if weighting == 'uniform':
            with contextlib.redirect_stdout(io.StringIO()):
                _noisiness = _ecurve.compute_noisiness()
            bpo_val = base_percentile_offset(_noisiness, size_sigma=_size_sigma)
            return (100.0 - bpo_val) / 100.0

        # Per-row noisiness → per-row bpo_ideal → SNR-weighted aggregate
        n_q, n_frames = self.M.shape
        x = np.arange(n_frames, dtype=float)
        n_knots = max(3, n_frames // 10) + 2
        knots = np.linspace(x[0], x[-1], n_knots)[1:-1]

        bpo_per_row = np.empty(n_q)
        for i in range(n_q):
            y = self.M[i, :].astype(float)
            scale = max(np.abs(y).max(), 1e-12)
            try:
                spline = LSQUnivariateSpline(x, y, knots)
                noisiness = np.std(y - spline(x)) / scale
            except Exception:
                noisiness = np.std(y) / scale
            bpo_val = base_percentile_offset(noisiness, size_sigma=_size_sigma)
            bpo_per_row[i] = (100.0 - bpo_val) / 100.0

        weights = self.get_snr_weights()
        if weights.sum() == 0:
            return float(np.mean(bpo_per_row))
        return float(np.average(bpo_per_row, weights=weights))

    def get_ideal_positive_ratio(self, weighting='snr'):
        """Expected positive_ratio for a perfect baseline, given this dataset's noise and peak geometry.

        Alias for ``get_bpo_ideal()`` with a self-documenting name.
        """
        return self.get_bpo_ideal(weighting=weighting)

    def evaluate_baseline(self, baseline, weighting='snr'):
        """Evaluate baseline quality in a single call.

        Parameters
        ----------
        baseline : ndarray
            2D baseline array with the same shape as self.M.
        weighting : {'snr', 'uniform'}

        Returns
        -------
        result : BaselineEvaluation
            Namedtuple with fields ``positive_ratio``, ``ideal``, ``delta``.
        """
        from collections import namedtuple
        BaselineEvaluation = namedtuple('BaselineEvaluation',
                                        ['positive_ratio', 'ideal', 'delta'])
        pr = self.get_positive_ratio(baseline, weighting=weighting)
        ideal = self.get_bpo_ideal(weighting=weighting)
        return BaselineEvaluation(pr, ideal, abs(pr - ideal))