"""
    DataObjects.SsMatrixData.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.DataObjects.Curve import create_icurve, create_jcurve

class SsMatrixData:
    def __init__(self, iv, jv, M, E):
        self.iv = iv
        if jv is None:
            jv = np.arange(M.shape[1])
        self.jv = jv
        self.M = M
        self.E = E      # may be None

    def copy(self, slices=None):
        if slices is None:
            islice = slice(None, None)
            jslice = slice(None, None)
        else:
            islice, jslice = slices
        Ecopy = None if self.E is None else self.E[islice,jslice].copy()
        return self.__class__(self.iv[islice].copy(),
                              self.jv[jslice].copy(),
                              self.M[islice,jslice].copy(),
                              Ecopy,
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

    def get_baseline2d(self, **kwargs):
        from molass.Baseline import Baseline2D
        method = kwargs.get('method', 'molass_lpm')
        if method == 'molass_lpm':
            moment = self.get_moment()
            default_kwargs = dict(moment=moment)
        else:
            default_kwargs = {}
        method_kwargs = kwargs.get('method_kwargs', default_kwargs)
        baseline_fitter = Baseline2D(moment.x, self.iv)
        baseline, params_not_used = baseline_fitter.individual_axes(
            self.M.T, axes=0, method=method, method_kwargs=method_kwargs
        )
        return baseline.T