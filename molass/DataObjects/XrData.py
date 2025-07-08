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
    XrData class for XR matrix data. """
    def __init__(self, iv, jv, M, E, **kwargs):
        super().__init__(iv, jv, M, E, **kwargs)
        self.qv = iv

    def get_ipickvalue(self):
        return PICKAT

    def get_icurve(self, pickat=PICKAT):
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

        Examples
        --------
        >>> curve = xr.get_icurve()

        >>> curve = xr.get_icurve(pickat=0.02)
        """
        return super().get_icurve(pickat)

    def get_usable_qrange(self, **kwargs):
        """xr.get_usable_qrange()
        
        Returns a pair of indeces which should be used
        as a slice for the angular axis to trim away
        unusable XR data regions. 

        Parameters
        ----------
        None
            
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

    def get_ibaseline(self, pickat=PICKAT, method=None, **kwargs):
        """xr.get_ibaseline(pickvalue=0.02)
        
        Returns a baseline i-curve from the XR matrix data.

        Parameters
        ----------
        pickvalue : float, optional
            See ssd.get_xr_icurve().

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
        
        Returns a Rg-curve.
        
        Parameters
        ----------
        None
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
        
        Returns an Rg-curve.
        
        Parameters
        ----------
        None
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