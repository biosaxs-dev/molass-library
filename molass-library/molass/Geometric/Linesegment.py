"""
    Geometric.Linesegment.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.stats import linregress
import ruptures as rpt

class Linesegment:
    """A class representing a line segment defined by linear regression.

    Attributes
    ----------
    slope : float
        The slope of the line segment.
    intercept : float
        The intercept of the line segment.
    std_err : float
        The standard error of the linear regression.
    x : array-like
        The x-values of the line segment.
    y : array-like
        The y-values of the line segment, computed as y = slope * x + intercept.
    center_x : float
        The center x-value of the line segment.
    center_y : float
        The center y-value of the line segment.
    """
    def __init__(self, x, y, regress_info=None):
        """Initialize the Linesegment object.
        Parameters
        ----------
        x : array-like
            The x-values of the line segment.
        y : array-like
            The y-values of the line segment.
        regress_info : tuple of (slope, intercept, std_err), optional
            Precomputed regression information. If None, it will be computed from x and y.
        """
        if regress_info is None:
            slope, intercept, r_value, p_value, std_err = linregress(x, y)
        else:
            slope, intercept, std_err = regress_info
        self.slope = slope
        self.intercept = intercept
        self.std_err = std_err
        self.x = x
        self.y = x*slope + intercept
        self.center_x = (x[0] + x[-1])/2
        self.center_y = (self.y[0] + self.y[-1])/2
    
    def get_std(self):
        """Get the standard error of the linear regression.
        Returns
        -------
        float
            The standard error of the linear regression.
        """
        return self.std_err
    
    def get_y(self):
        """Get the y-values of the line segment.
        Returns
        -------
        array-like
            The y-values of the line segment.
        """
        return self.y
    
    def __neg__(self):
        return Linesegment(self.x, -self.y, regress_info=(-self.slope, -self.intercept, self.std_err))

def get_segments(x, y, breakpoints=None, n_bkps=2):
    """Segment the data into line segments using change point detection.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    breakpoints : list of int, optional
        The breakpoints for segmentation. If None, they will be computed using change point detection.
    n_bkps : int, optional
        The number of breakpoints to detect if breakpoints is None. Default is 2.

    Returns
    -------
    tuple
        A tuple containing the list of breakpoints and the list of Linesegment objects.
    """
    if breakpoints is None:
        algo = rpt.Dynp(model="l1", min_size=10).fit(y)
        breakpoints = algo.predict(n_bkps=n_bkps)
    
    segments = []
    start = None
    for k in range(n_bkps+1):
        stop = breakpoints[k] if k < n_bkps else None
        seg = Linesegment(x[start:stop], y[start:stop])
        segments.append(seg)
        start = stop

    return breakpoints[0:n_bkps], segments

def plot_segments(x, y, segments, title=None, ax=None):
    """Plot the data and the line segments.
    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    segments : list of Linesegment
        The list of line segments to plot.
    title : str, optional
        The title of the plot. If None, no title is set.
    ax : matplotlib.axes.Axes, optional
        The axes to plot on. If None, a new figure and axes are created.
    """
    if ax is None:
        import matplotlib.pyplot as plt 
        fig, ax = plt.subplots()
    if title is not None:
        ax.set_title(title)
    ax.plot(x, y)
    for seg in segments:
        ax.plot(seg.x[[0,-1]], seg.y[[0,-1]], 'o:', lw=2)

def to_negative_segments(segments):
    """Convert a list of line segments to their negative counterparts.
    
    Parameters
    ----------
    segments : list of Linesegment
        The list of line segments to convert.
    Returns
    -------
    list of Linesegment
        The list of negative line segments.
    """
    ret_segments = []
    for seg in segments:
        ret_segments.append(-seg)
    return ret_segments