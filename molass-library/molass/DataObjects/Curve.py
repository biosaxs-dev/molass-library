"""
    DataObjects.Curve.py
"""
import numpy as np
from bisect import bisect_right

class Curve:
    """A class representing a 1D curve with x and y data.
    
    Attributes
    ----------
    x : array-like
        The x-values of the curve.
    y : array-like
        The y-values of the curve.
    type : str or None
        The type of the curve, e.g., 'i' for intensity curves.  If None, the type is unspecified.
    max_i : int or None
        The index of the maximum y-value. Computed on demand. If None, it has not been computed yet.
    max_x : float or None
        The x-value corresponding to the maximum y-value. Computed on demand. If None, it has not been computed yet.
    max_y : float or None
        The maximum y-value. Computed on demand. If None, it has not been computed yet.
    peaks : list of int or None
        The indices of the peaks in the curve. Computed on demand. If None, it has not been computed yet.
    moment : Moment or None
        The moment of the curve. Computed on demand. If None, it has not been computed yet.
    spline : UnivariateSpline or None
        A spline representation of the curve. Computed on demand. If None, it has not been computed yet.
    diff_spline : UnivariateSpline or None
        The derivative spline representation of the curve. Computed on demand. If None, it has not been computed yet.
        
    """
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
        """Return the x and y data as a tuple.

        Returns
        -------
        tuple
            A tuple containing the x and y data.
        """
        return self.x, self.y

    def set_max(self):
        """Set the maximum value and its index."""
        m = np.argmax(self.y)
        self.max_i = m
        self.max_x = self.x[m]
        self.max_y = self.y[m]

    def get_max_i(self):
        """Get the index of the maximum y value."""
        if self.max_i is None:
            self.set_max()
        return self.max_i

    def get_max_y(self):
        """Get the maximum y value."""
        if self.max_y is None:
            self.set_max()
        return self.max_y

    def get_max_x(self):
        """Get the x value corresponding to the maximum y value."""
        if self.max_x is None:
            self.set_max()
        return self.max_x

    def get_max_xy(self):
        """Get the (x, y) pair corresponding to the maximum y value."""
        if self.max_y is None:
            self.set_max()
        return self.max_x, self.max_y

    def get_peaks(self, debug=False, **kwargs):
        """
        Get the peak positions.
        
        Parameters
        ----------
        debug : bool, optional
            If True, enable debug mode.
        
        Returns
        -------
        list of int
            The list of peak positions (indices of self.x).
        """
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
        """
        Get the number of major peaks.
        """
        peaks = self.get_peaks(**kwargs)
        return len(peaks)

    def get_moment(self):
        """Get the moment of the curve.
        Returns
        -------
        moment: Moment
            The moment object representing the moment of the curve.
        """
        if self.moment is None:
            from molass.Stats.Moment import Moment
            self.moment = Moment(self.x, self.y)
        return self.moment

    def smooth_copy(self):
        """Return a smoothed copy of the curve.
        This is a placeholder for actual smoothing logic."""
        from molass_legacy.KekLib.SciPyCookbook import smooth
        y = smooth(self.y)
        return Curve(self.x, y, type=self.type)

    def get_spline(self):
        """Get a spline representation of the curve."""
        from scipy.interpolate import UnivariateSpline
        if self.spline is None:
            self.spline = UnivariateSpline(self.x, self.y, s=0, ext=3)
        return self.spline

    def get_diff_spline(self):
        """Get the derivative of the spline representation of the curve."""
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
    """Create an i-curve from a 2D matrix M by picking a row based on pickvalue.

    Parameters
    ----------
    x : array-like or None
        The x values for the curve. If None, defaults to np.arange(M.shape[1]).
    M : 2D array-like
        The 2D matrix from which to extract the i-curve.
    vector : array-like
        The vector used to determine which row to pick based on pickvalue. Must be sorted.
    pickvalue : float
        The value used to select the appropriate row from M.

    Returns
    -------
    Curve
        The resulting i-curve.
    """
    if x is None:
        x = np.arange(M.shape[1])
    i = bisect_right(vector, pickvalue)
    y = M[i,:]
    return Curve(x, y, type='i')

def create_jcurve(x, M, j):
    """Create a j-curve from a 2D matrix M by picking a column j.

    Parameters
    ----------
    x : array-like or None
        The x values for the curve. If None, defaults to np.arange(M.shape[0]).
    M : 2D array-like
        The 2D matrix from which to extract the j-curve.
    j : int
        The column index to extract.
        
    Returns
    -------
    Curve
        The resulting j-curve.
    """
    y = M[:,j]
    return Curve(x, y, type='j')