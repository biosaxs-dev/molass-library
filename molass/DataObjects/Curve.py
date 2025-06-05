"""
    DataObjects.Curve.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from bisect import bisect_right

class Curve:
    def __init__(self, x, y, type=None):
        assert len(x) == len(y)
        self.x = x
        self.y = y
        self.max_i = None
        self.max_x = None
        self.max_y = None
        self.type = type
        self.spline = None
        self.__rmul__ = self.__mul__

    def __add__(self, rhs):
        assert len(self.x) == len(rhs.x)
        return Curve(self.x, self.y + rhs.y, type=self.type)

    def __sub__(self, rhs):
        assert len(self.x) == len(rhs.x)
        return Curve(self.x, self.y - rhs.y, type=self.type)

    def __mul__(self, rhs):
        if type(rhs) is Curve:
            y_ = self.y * rhs.y
        else:
            y_ = self.y * rhs
        return Curve(self.x, y_, type=self.type)

    def get_xy(self):
        return self.x, self.y

    def set_max(self):
        m = np.argmax(self.y)
        self.max_i = m
        self.max_x = self.x[m]
        self.max_y = self.y[m]

    def get_max_i(self):
        if self.max_i is None:
            self.set_max()
        return self.max_i

    def get_max_xy(self):
        if self.max_y is None:
            self.set_max()
        return self.max_x, self.max_y

    def get_peaks(self, debug=False):
        if debug:
            from importlib import reload
            import molass.Peaks.Recognizer
            reload(molass.Peaks.Recognizer)
        from molass.Peaks.Recognizer import get_peak_positions
        if self.type != 'i':
            raise TypeError("get_peaks works only for i-curves")
        return get_peak_positions(self, debug=debug)

    def smooth_copy(self):
        from molass_legacy.KekLib.SciPyCookbook import smooth
        y = smooth(self.y)
        return Curve(self.x, y, type=self.type)

    def get_spline(self):
        from scipy.interpolate import UnivariateSpline
        if self.spline is None:
            self.spline = UnivariateSpline(self.x, self.y, s=0, ext=3)
        return self.spline

def create_icurve(x, M, vector, pickvalue):
    if x is None:
        x = np.arange(M.shape[1])
    i = bisect_right(vector, pickvalue)
    y = M[i,:]
    return Curve(x, y, type='i')

def create_jcurve(x, M, j):
    y = M[:,j]
    return Curve(x, y, type='j')