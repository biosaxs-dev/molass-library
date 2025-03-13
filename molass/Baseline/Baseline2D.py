"""
    Baseline.Baseline2D.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from pybaselines import Baseline2D as _Baseline2D

class Baseline2D(_Baseline2D):
    """A LPM-specialized class for 2D baseline fitting"""

    def __init__(self, x, y):
        """Same as the parent class"""
        super().__init__(x, y)

    def individual_axes(self, data, axes=(0, 1), method='asls', method_kwargs=None, debug=True):
        """Override the method to use LPM baseline fitting"""
        if method == 'molass_lpm':
            if debug:
                from importlib import reload
                import molass.Baseline.LpmBaseline2D
                reload(molass.Baseline.LpmBaseline2D)
            from molass.Baseline.LpmBaseline2D import individual_axes_impl
            return individual_axes_impl(self, data, axes, method, method_kwargs)
        else:
            return super().individual_axes(data, axes, method, method_kwargs)