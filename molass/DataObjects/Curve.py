"""
    DataObjects.Curve.py
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
        self.peaks = None
        self.moment = None
        self.spline = None
        self.diff_spline = None
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

    def get_max_y(self):
        if self.max_y is None:
            self.set_max()
        return self.max_y

    def get_max_x(self):
        if self.max_x is None:
            self.set_max()
        return self.max_x

    def get_max_xy(self):
        if self.max_y is None:
            self.set_max()
        return self.max_x, self.max_y

    def get_peaks(self, debug=False, **kwargs):
        if self.peaks is None:
            if debug:
                from importlib import reload
                import molass.Peaks.Recognizer
                reload(molass.Peaks.Recognizer)
            from molass.Peaks.Recognizer import get_peak_positions
            if self.type != 'i':
                raise TypeError("get_peaks works only for i-curves")
            self.peaks = get_peak_positions(self, debug=debug, **kwargs)
        return self.peaks

    def get_num_major_peaks(self, **kwargs):
        peaks = self.get_peaks(**kwargs)
        return len(peaks)

    def get_moment(self):
        if self.moment is None:
            from molass.Stats.Moment import Moment
            self.moment = Moment(self.x, self.y)
        return self.moment

    def smooth_copy(self):
        from molass_legacy.KekLib.SciPyCookbook import smooth
        y = smooth(self.y)
        return Curve(self.x, y, type=self.type)

    def get_spline(self):
        from scipy.interpolate import UnivariateSpline
        if self.spline is None:
            self.spline = UnivariateSpline(self.x, self.y, s=0, ext=3)
        return self.spline

    def get_diff_spline(self):
        if self.diff_spline is None:
            spline = self.get_spline()
            self.diff_spline = spline.derivative()
        return self.diff_spline

    def corrected_copy(self):
        """
        Return a copy of the curve with corrected x values.
        This is a placeholder for actual correction logic.
        """
        assert self.type == 'i', "corrected_copy works only for i-curves"
        from molass_legacy.DataStructure.LPM import get_corrected
        y = get_corrected(self.y, x=self.x)
        return Curve(self.x, y, type=self.type)

def create_icurve(x, M, vector, pickvalue):
    if x is None:
        x = np.arange(M.shape[1])
    i = bisect_right(vector, pickvalue)
    y = M[i,:]
    return Curve(x, y, type='i')

def create_jcurve(x, M, j):
    y = M[:,j]
    return Curve(x, y, type='j')