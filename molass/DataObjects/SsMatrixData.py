"""
    DataObjects.SsMatrixData.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.DataObjects.Curve import create_icurve, create_jcurve

class SsMatrixData:
    def __init__(self, iv, jv, M, E,
                 moment=None,
                 baseline_method='linear'):
        self.iv = iv
        if jv is None:
            jv = np.arange(M.shape[1])
        self.jv = jv
        self.M = M
        self.E = E      # may be None
        self.moment = moment
        self.baseline_method = baseline_method

    def copy(self, slices=None):
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
        return create_icurve(self.jv, self.M, self.iv, pickat)
    
    def get_jcurve(self, j):
        """sd.get_jcurve(j)
        
        Returns a j-curve from the XR matrix data.

        Parameters
        ----------
        j : int
            Specifies the index to pick a j-curve.
            The j-curve will be made from ssd.xrM[:,j].
            
        Examples
        --------
        >>> curve = sd.get_jcurve(150)
        """
        return create_jcurve(self.iv, self.M, j)

    def get_moment(self):
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