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
        If True, the endpoint-anchored LPM baseline is used automatically
        (equivalent to ``endpoint_fraction=0.15``) to avoid contamination
        from physically real negative-peak frames.  Default False.
    """
    def __init__(self, M, iv, jv, E=None,
                 moment=None,
                 baseline_method='linear',
                 allow_negative_peaks=False):
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
        self.allow_negative_peaks = allow_negative_peaks

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
                            allow_negative_peaks=self.allow_negative_peaks,
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

    def set_allow_negative_peaks(self, value=True):
        """Declare that this dataset contains physically real negative peaks.

        When True, ``get_baseline2d()`` automatically uses the
        endpoint-anchored LPM (``endpoint_fraction=0.15``) instead of the
        standard bottom-percentile anchor, which would be contaminated by
        negative-peak frames.

        This flag is propagated by ``copy()`` and ``corrected_copy()``, so
        the typical workflow is::

            ssd.set_allow_negative_peaks()
            ssd.plot_compact(baseline=True)   # inspect endpoint-anchored baseline
            corrected = ssd.corrected_copy()  # applies it — no extra args needed

        Parameters
        ----------
        value : bool, optional
            Default True.
        """
        self.allow_negative_peaks = value

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
            frames.  Use this for datasets with physically real negative peaks
            (where the standard LPM anchor would be contaminated by those
            frames).  Default ``None`` — standard LPM unchanged.
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
        >>> bl = xr.get_baseline2d(endpoint_fraction=0.15)  # one-off override
        >>> xr.set_allow_negative_peaks()                   # preferred: store as state
        >>> bl = xr.get_baseline2d()                        # endpoint-anchored automatically
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
            if endpoint_fraction is None and self.allow_negative_peaks:
                endpoint_fraction = 0.15
            if endpoint_fraction is not None:
                default_kwargs['endpoint_fraction'] = endpoint_fraction
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

    def get_positive_ratio(self, baseline, weighting='snr'):
        """Fraction of non-negative residual elements, optionally SNR-weighted.

        Parameters
        ----------
        baseline : ndarray
            2D baseline array with the same shape as self.M.
        weighting : {'snr', 'uniform'}
            'snr' (default) weights each q-row by its SNR so that
            informative low-q rows dominate over noisy high-q rows.

        Returns
        -------
        positive_ratio : float
        """
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