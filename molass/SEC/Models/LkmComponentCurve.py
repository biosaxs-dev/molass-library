"""
SEC.Models.LkmComponentCurve.py

LKM (Lumped Kinetic Model) component curve.

Each component stores its own (R, k_MT) while sharing (Pe, t0) across all
components in the same decomposition.

Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from molass.LowRank.ComponentCurve import ComponentCurve


class LkmComponentCurve(ComponentCurve):
    """
    A class to represent an LKM component curve.

    Attributes
    ----------
    x : array-like
        The x values (frame numbers).
    Pe : float
        Péclet number (shared column parameter).
    t0 : float
        Dead time in frame units (shared column parameter).
    k_MT : float
        Mass-transfer rate for this component.
    R : float
        Retention factor for this component (R = tR / t0 ≥ 1).
    scale : float
        Area scaling factor.
    rg : float, optional
        Radius of gyration for this component (used by rigorous optimizer).
    """

    model = 'lkm'

    def __init__(self, x, Pe, t0, k_MT, R, scale, rg=None):
        """
        Initializes the LkmComponentCurve.

        Parameters
        ----------
        x : array-like
            Frame-number axis.
        Pe : float
            Péclet number.
        t0 : float
            Dead time (frame units).
        k_MT : float
            Mass-transfer rate.
        R : float
            Retention factor (R = tR / t0).
        scale : float
            Area scale factor.
        rg : float, optional
            Radius of gyration (stored for downstream Guinier analysis).
        """
        from molass.SEC.Models.LkmLinear import lkm_pdf
        self.x = x
        self.Pe = Pe
        self.t0 = t0
        self.k_MT = k_MT
        self.R = R
        self.scale = scale
        self.rg = rg if rg is not None else float('nan')
        self.moment = None
        self.params = np.array([Pe, t0, k_MT, R, scale])  # flat params for compatibility

        self._lkm_pdf = lkm_pdf
        self._y = scale * lkm_pdf(x, Pe, t0, k_MT, R)

    @property
    def y(self):
        """The y-values of the component curve evaluated at self.x."""
        return self._y

    def get_y(self, x=None):
        """
        Returns the y-values.

        Parameters
        ----------
        x : array-like or None
            If None, returns precomputed y at self.x.

        Returns
        -------
        array-like
        """
        if x is None:
            return self._y
        return self.scale * self._lkm_pdf(x, self.Pe, self.t0, self.k_MT, self.R)

    def get_scale_param(self):
        return self.scale

    def get_peak_top_x(self):
        return self.x[np.argmax(self._y)]

    def get_params(self):
        """Return (Pe, t0, k_MT, R, scale) as a tuple."""
        return (self.Pe, self.t0, self.k_MT, self.R, self.scale)
