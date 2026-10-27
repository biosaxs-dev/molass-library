"""
    Mapping.Mapping.py
"""
import numpy as np


class Mapping:
    """The linear XR->UV frame mapping ``uv = a * xr + b``.

    ``slope`` / ``intercept`` / ``xr_to_uv`` / ``uv_to_xr`` are the names used by
    :class:`molass.Mapping.MappingInfo.MappingInfo` (the estimate returned by
    ``SecSaxsData.estimate_mapping()``); ``a`` / ``b`` / ``__call__`` / ``inv`` are kept.
    Both unpack to ``(slope, intercept)``.
    """
    def __init__(self, a, b):
        self.a = a
        self.b = b

    @property
    def slope(self):
        return self.a

    @property
    def intercept(self):
        return self.b

    def __call__(self, x):
        return self.a * x + self.b

    def inv(self, y):
        return (y - self.b) / self.a

    def xr_to_uv(self, x):
        """XR frame number(s) to UV frame number(s) (same as calling the mapping)."""
        return self.a * np.asarray(x) + self.b

    def uv_to_xr(self, y):
        """UV frame number(s) to XR frame number(s) (same as :meth:`inv`)."""
        return (np.asarray(y) - self.b) / self.a

    def __iter__(self):
        """Allow unpacking of Mapping to (a, b)."""
        return iter((self.a, self.b))

    def __repr__(self):
        return f"Mapping(slope={self.a:.4g}, intercept={self.b:.4g})"
