"""
    DataObjects.UvData.py
"""
from molass.DataObjects.SsMatrixData import SsMatrixData
from molass.DataObjects.Curve import Curve

PICKVALUES = [280, 400]
PICKAT = PICKVALUES[0]

class UvData(SsMatrixData):
    """
    UvData class for UV matrix data. 
    Inherits from SsMatrixData.

    Attributes
    ----------
    wv : array-like
        The wavelength values corresponding to the spectral axis (iv). Alias: ``wavelengths``.
    wavelengths : array-like (property)
        Human-readable alias for ``iv`` / ``wv`` — the wavelength axis (nm).
    frames : array-like (property)
        Human-readable alias for ``jv`` — the frame (time) axis.

    Notes
    -----
    Matrix ``M`` has shape ``(len(wavelengths), len(frames))``:
    rows index wavelength, columns index frame number.

    """
    def __init__(self, iv, jv, M, E, **kwargs):
        """Initialize the UvData object.
        
        Parameters
        ----------
        iv : array-like
            The wavelength values corresponding to the spectral axis.
        jv : array-like
            The values corresponding to the temporal axis.
        M : 2D array-like
            The 2D matrix of intensity values.
        E : 2D array-like or None
            The 2D matrix of error values. It can be None if errors are not available.
        kwargs : dict, optional
            Additional keyword arguments to pass to the SsMatrixData constructor.
        """
        super().__init__(iv, jv, M, E, **kwargs)
        self.wv = iv
        self.pickat = PICKAT

    @property
    def uv_pickat(self):
        """Alias for ``pickat`` — the default wavelength (nm) for i-curve extraction."""
        return self.pickat

    @uv_pickat.setter
    def uv_pickat(self, value):
        self.pickat = value

    @property
    def wavelengths(self):
        """Wavelength axis in nm (alias for ``iv`` / ``wv``)."""
        return self.iv

    @property
    def frames(self):
        """Frame (time) axis (alias for ``jv``)."""
        return self.jv

    @property
    def wavelength_range(self):
        """Wavelength coverage as ``(min, max)`` in nm."""
        return (self.wavelengths.min(), self.wavelengths.max())

    def __repr__(self):
        wl_min, wl_max = self.wavelength_range
        return (
            f"UvData: M shape (wavelengths={len(self.wavelengths)}, frames={len(self.frames)})"
            f"  wv range {wl_min:.0f}-{wl_max:.0f} nm"
        )

    def copy(self, slices=None):
        result = super().copy(slices=slices)
        result.pickat = self.pickat
        return result

    def get_recognition_curve(self):
        """uv.get_recognition_curve()

        Return the elution curve at ``self.pickat`` wavelength (default 280 nm,
        or the value set via ``SSD(uv_pickat=...)``).

        Unlike XR where ``M.sum(axis=0)`` is a useful alternative, UV sum
        across all wavelengths is dominated by noise from non-absorbing
        channels and is not appropriate for peak/buffer classification.

        Returns
        -------
        Curve
            The recognition elution curve at the selected wavelength.
        """
        return self.get_icurve()

    def get_ipickvalues(self):
        """Get the default pickvalues for i-curves.
        Returns
        -------
        list
            The default pickvalues for i-curves.
        """
        return PICKVALUES

    def get_icurve(self, pickat=None):
        """uv_data.get_icurve(pickat=280)
        
        Returns an i-curve from the UV matrix data.

        Parameters
        ----------
        pickat : float, optional
            Specifies the wavelength (nm) at which to pick an i-curve.
            The i-curve will be made from self.M[i,:] where
            the picking index i will be determined to satisfy
                self.wv[i-1] <= pickat < self.wv[i]
            according to bisect_right.
            If None, uses self.pickat (default 280 nm, or the value set
            via SSD(uv_pickat=...)).

        Examples
        --------
        >>> curve = uv_data.get_icurve()
        """
        if pickat is None:
            pickat = self.pickat
        return super().get_icurve(pickat)

    def get_flowchange_points(self, pickvalues=PICKVALUES, return_also_curves=False):
        """uv.get_flowchange_points()

        Returns a pair of flowchange points.

        Parameters
        ----------
        pickvalues: list
            specifies the pickvalues of icurves which are used to detect
            the flowchange points.

        return_also_curves: bool
            If it is False, the method returns only a list of indeces of points.
            If it is True, the method returns a list indeces of points and
            a list of curves which were used to detect the points.
        
        Examples
        --------
        >>> i, j = uv.get_flowchange_points()        
        """
        from molass.FlowChange.FlowChange import flowchange_exclude_slice
        curves = []
        for pickvalue in pickvalues:
            curve = self.get_icurve(pickat=pickvalue)
            curves.append(curve)
        points, judge_info = flowchange_exclude_slice(curves[0], curves[1])
        if return_also_curves:
            return points, judge_info, curves
        else:
            return points, judge_info

    def get_usable_wrange(self):
        """uv.get_usable_wrange()
        
        Returns a pair of indeces which should be used
        as a slice for the spectral axis to trim away
        unusable UV data regions. 

        Parameters
        ----------
        None
            
        Examples
        --------
        >>> i, j = uv.get_usable_wrange()
        """
        from molass.Trimming.UsableWrange import get_usable_wrange_impl
        return get_usable_wrange_impl(self)

    def get_ibaseline(self, pickat=None, method=None, **kwargs):
        """uv.get_ibaseline()
        
        Returns a baseline i-curve from the UV matrix data.

        Parameters
        ----------
        pickat : float, optional
            Wavelength (nm) at which to pick the i-curve for baseline fitting.
            If None, uses self.pickat (default 280 nm, or the value set
            via SSD(uv_pickat=...)).

        method : str, optional
            The baseline method to use. If None, the method set in
            self.baseline_method will be used.

        debug : bool, optional
            If True, enable debug mode.

        kwargs : dict, optional
            Additional keyword arguments to pass to the baseline fitting method.
            These will be merged with the default_kwargs defined above.

        Returns
        -------
        baseline: Curve
            
        Examples
        --------
        >>> curve = uv.get_icurve()
        >>> baseline = uv.get_ibaseline()
        >>> corrected_curve = curve - baseline
        """
        debug = kwargs.get('debug', False)
        if debug:
            from importlib import reload
            import molass.Baseline.BaselineUtils
            reload(molass.Baseline.BaselineUtils)
        from molass.Baseline.BaselineUtils import get_uv_baseline_func
        icurve = self.get_icurve(pickat=pickat)
        if method is None:
            method = self.get_baseline_method()
        compute_baseline_impl = get_uv_baseline_func(method)
        kwargs['moment'] = self.get_moment()
        if method == 'uvdiff':
            from molass.Baseline.UvdiffBaseline import get_uvdiff_baseline_info
            uvdiff_info = get_uvdiff_baseline_info(self)
            kwargs['uvdiff_info'] = uvdiff_info
        y = compute_baseline_impl(icurve.x, icurve.y, **kwargs)
        return Curve(icurve.x, y, type='i')