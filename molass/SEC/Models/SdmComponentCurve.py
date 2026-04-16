"""
    SEC.Models.SdmComponentCurve.py

"""
import numpy as np
from molass.SEC.Models.SdmMonoPore import (
    sdm_monopore_pdf,
    sdm_monopore_gamma_pdf,
    DEFAULT_TIMESCALE,
)
from molass.LowRank.ComponentCurve import ComponentCurve

class SdmColumn:
    """
    A class to represent an SDM column.

    Attributes
    ----------
    params : tuple
        The parameters of the SDM column.

        - ``pore_dist='mono'``:      ``(N, T, me, mp, x0, tI, N0, poresize, timescale, k)``
        - ``pore_dist='lognormal'``:  ``(N, T, me, mp, x0, tI, N0, mu, sigma, k)``

        Positions 0–6 and 9 are shared; positions 7–8 differ by pore_dist.
    pore_dist : str
        Pore-size distribution: ``'mono'`` (default) or ``'lognormal'``.
    rt_dist : str
        Residence-time distribution: ``'exponential'`` or ``'gamma'`` (default).
    """
    def __init__(self, params, pore_dist='mono', rt_dist='gamma'):
        """
        Initializes the SDM column.

        Parameters
        ----------
        params : tuple
            The column parameters:

            - ``pore_dist='mono'``:      ``(N, T, me, mp, x0, tI, N0, poresize, timescale, k)``
            - ``pore_dist='lognormal'``:  ``(N, T, me, mp, x0, tI, N0, mu, sigma, k)``

            If k is omitted (9 elements), defaults to 1.0 (exponential, backward compatible).
        pore_dist : str, optional
            Pore-size distribution: ``'mono'`` (default) or ``'lognormal'``.
        rt_dist : str, optional
            Residence-time distribution: ``'exponential'`` or ``'gamma'`` (default).
        """
        if len(params) == 9:
            # backward compatible: mono-pore (k=1)
            params = list(params) + [1.0]
        self.params = params
        self.pore_dist = pore_dist
        self.rt_dist = rt_dist

    def get_params(self):
        """
        Returns the parameters of the SDM column.

        Returns
        -------
        tuple
            The parameters of the SDM column.
        """
        return self.params

class SdmComponentCurve(ComponentCurve):
    """
    A class to represent an SDM component curve.

    Attributes
    ----------
    x : array-like
        The x values.
    params : tuple
        The parameters of the SDM column (N, T, me, mp, x0, tI, N0, poresize, timescale).
    """
    def __init__(self, x, column, rg, scale):
        """
        Initializes the SDM component curve.

        Parameters
        ----------
        x : array-like
            The x values.
        column : SdmColumn
            The SDM column object containing the parameters.
        rg : float
            The radius of gyration for this component.
        scale : float
            The scaling factor.
        """
        self.column = column
        self.rg = rg
        self.x = x
        self.moment = None
        self.model = 'sdm'

        if column.pore_dist == 'lognormal':
            from molass.SEC.Models.LognormalPore import (
                sdm_lognormal_pore_pdf,
                sdm_lognormal_pore_gamma_pdf_fast,
            )
            # params: (N, T, me, mp, x0, tI, N0, mu, sigma, k)
            N, T, me, mp, x0, tI, N0, mu, sigma, k = column.get_params()
            self.tI = tI
            self._x = x - tI
            t0 = x0 - tI
            if column.rt_dist == 'exponential':
                self.params = (1.0, N, T, me, mp, mu, sigma, rg, N0, t0)
                self._pdf_func = sdm_lognormal_pore_pdf
            else:
                self.params = (1.0, N, T, k, me, mp, mu, sigma, rg, N0, t0)
                self._pdf_func = sdm_lognormal_pore_gamma_pdf_fast
        else:
            # params: (N, T, me, mp, x0, tI, N0, poresize, timescale, k)
            N, T, me, mp, x0, tI, N0, poresize, timescale, k = column.get_params()
            self.tI = tI
            self._x = x - tI
            rho = rg/poresize
            if rho > 1.0:
                rho = 1.0
            ni = N*(1 - rho)**me
            ti = T*(1 - rho)**mp
            t0 = x0 - tI
            if column.rt_dist == 'exponential':
                self.params = (ni, ti, N0, t0, timescale)
                self._pdf_func = sdm_monopore_pdf
            else:
                theta = ti / k  # Gamma scale: mean = k*theta = ti
                self.params = (ni, k, theta, N0, t0, timescale)
                self._pdf_func = sdm_monopore_gamma_pdf
        self.scale = scale
    
    def get_y(self, x=None):
        """
        Returns the y values for the given x values.

        Parameters
        ----------
        x : array-like or None, optional
            The x values to get the y values for. If None, uses the object's x values.

        Returns
        -------
        array-like
            The y values corresponding to the given x values.
        """
        if x is None:
            _x = self._x
        else:
            _x = x - self.tI
        return self.scale * self._pdf_func(_x, *self.params)
    
    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.

        Raises
        ------
        NotImplementedError
            Peak top x calculation is not implemented for SDM model.
        """
        raise NotImplementedError("Peak top x calculation is not implemented for SDM model.")
    
    def get_scale_param(self):
        """
        Returns the scale parameter.

        Returns
        -------
        float
            The scale parameter.
        """
        return self.scale