"""
    Baseline.Surface.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np

class Surface:
    def __init__(self, x, y, add_spline=False):
        self.Z = x[:,np.newaxis] @ y[np.newaxis,:]
        if add_spline:
            from scipy.interpolate import RectBivariateSpline
            self.spline = RectBivariateSpline(x, y, self.Z)
        else:
            self.spline = None

    def get(self):
        return self.Z

    def __call__(self, x, y):
        assert self.spline is not None
        return self.spline(x, y)