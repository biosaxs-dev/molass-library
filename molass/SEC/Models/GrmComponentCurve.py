"""
SEC.Models.GrmComponentCurve.py

GRM (General Rate Model) component curve.

Each component stores its own (R, k_ext) while sharing (Pe, t0, R_p, D_eff)
across all components in the same decomposition.

Copyright (c) 2026, SAXS Team, KEK-PF
"""
import numpy as np
from molass.LowRank.ComponentCurve import ComponentCurve


class GrmComponentCurve(ComponentCurve):
    """
    A component curve computed from the General Rate Model (GRM).

    Attributes
    ----------
    x : array-like
        Frame-number axis.
    Pe : float
        Péclet number (shared column parameter).
    t0 : float
        Dead time in frame units (shared column parameter).
    R_p : float
        Particle radius (shared column parameter, same units as k_ext).
    D_eff : float
        Effective intraparticle pore diffusivity (shared, [length²/time]).
    a_star : float
        Effective intraparticle retention parameter (shared):
        a_star = eps_p + (1 - eps_p) * a_henry
    F_ratio : float
        Phase ratio F = (1-ε)/ε (shared column parameter).
    k_ext : float
        External film mass-transfer coefficient for this component [length/time].
    R : float
        Retention factor for this component (R = tR/t0 = 1 + F*a_star).
    scale : float
        Area scaling factor.
    rg : float, optional
        Radius of gyration for this component.
    """

    model = 'grm'

    def __init__(self, x, Pe, t0, R_p, D_eff, a_star, F_ratio, k_ext, R, scale, rg=None):
        from molass.SEC.Models.GrmLinear import grm_pdf
        self.x       = x
        self.Pe      = Pe
        self.t0      = t0
        self.R_p     = R_p
        self.D_eff   = D_eff
        self.a_star  = a_star
        self.F_ratio = F_ratio
        self.k_ext   = k_ext
        self.R       = R
        self.scale   = scale
        self.rg      = rg if rg is not None else float('nan')
        self.moment  = None
        self.params  = np.array([Pe, t0, R_p, D_eff, a_star, F_ratio, k_ext, R, scale])

        self._grm_pdf = grm_pdf
        self._y = scale * grm_pdf(x, Pe, t0, k_ext, R_p, D_eff, a_star, F_ratio)

    @property
    def y(self):
        return self._y

    def get_y(self, x=None):
        if x is None:
            return self._y
        return self.scale * self._grm_pdf(x, self.Pe, self.t0, self.k_ext,
                                          self.R_p, self.D_eff, self.a_star, self.F_ratio)

    def get_xy(self):
        return self.x, self._y

    def get_peak_position(self):
        """Return the x-position of the PDF maximum (mode)."""
        return self.x[np.argmax(self._y)]

    def get_scale_param(self):
        """Return the area scaling factor (overrides base-class params[0] which is Pe)."""
        return self.scale
