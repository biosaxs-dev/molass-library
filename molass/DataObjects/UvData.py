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
        The wavelength values corresponding to the spectral axis (iv).

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

    def get_ipickvalues(self):
        """Get the default pickvalues for i-curves.
        Returns
        -------
        list
            The default pickvalues for i-curves.
        """
        return PICKVALUES

    def get_icurve(self, pickat=PICKAT):
        """uv_data.get_icurve(pickat=280)
        
        Returns an i-curve from the UV matrix data.

        Parameters
        ----------
        pickat : float, optional
            Specifies the value in ssd.qv where to pick an i-curve.
            The i-curve will be made from self.M[i,:] where
            the picking index i will be determined to satisfy
                self.wv[i-1] <= pickat < self.vec.wv[i]
            according to bisect_right.

        Examples
        --------
        >>> curve = uv_data.get_icurve()
        """
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

    def get_ibaseline(self, pickat=PICKAT, method=None, **kwargs):
        """uv.get_uv_ibaseline(pickvalue=0.02)
        
        Returns a baseline i-curve from the UV matrix data.

        Parameters
        ----------
        pickvalue : float, optional
            See uv.get_icurve().

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