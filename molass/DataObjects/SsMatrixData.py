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
    E : 2D array-like or None
        The 2D matrix of error values. It can be None if errors are not available
    moment : Moment or None
        The moment of the data along the iv axis. It can be None if not computed.
    baseline_method : str
        The method used for baseline correction. Default is 'linear'.
    """
    def __init__(self, iv, jv, M, E,
                 moment=None,
                 baseline_method='linear'):
        """Initialize the SsMatrixData object."""
        self.iv = iv
        if jv is None:
            jv = np.arange(M.shape[1])
        self.jv = jv
        self.M = M
        self.E = E      # may be None
        self.moment = moment
        self.baseline_method = baseline_method

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
                            self.iv[islice].copy(),
                            self.jv[jslice].copy(),
                            self.M[islice,jslice].copy(),
                            Ecopy,
                            moment=None,  # note that moment is not copied
                            baseline_method=self.baseline_method,
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

    def get_baseline2d(self, **kwargs):
        """Get the 2D baseline for the matrix data using the specified method.

        Parameters
        ----------
        method_kwargs : dict, optional
            Additional keyword arguments to pass to the baseline fitting method.
        debug : bool, optional
            If True, enable debug mode.
            
        Returns
        -------
        baseline : ndarray
            The 2D baseline array with the same shape as self.M.
        """
        from molass.Baseline import Baseline2D
        debug = kwargs.get('debug', False)
        counter = [0, 0, 0] if debug else None
        if self.baseline_method in ['linear', 'uvdiff', 'integral']:
            default_kwargs = dict(jv=self.jv, ssmatrix=self, counter=counter)
            if self.baseline_method == 'uvdiff':
                from molass.Baseline.UvdiffBaseline import get_uvdiff_baseline_info
                default_kwargs['uvdiff_info'] = get_uvdiff_baseline_info(self)
        else:
            default_kwargs = {}
        method_kwargs = kwargs.get('method_kwargs', default_kwargs)
        baseline_fitter = Baseline2D(self.jv, self.iv)
        baseline, params_not_used = baseline_fitter.individual_axes(
            self.M.T, axes=0, method=self.baseline_method, method_kwargs=method_kwargs
        )
        if debug:
            if counter is not None:
                print(f"Baseline fitting completed with {counter} iterations.")  
        return baseline.T