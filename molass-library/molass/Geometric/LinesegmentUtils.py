"""
    Geometric.LinesegmentUtils.py
"""
import numpy as np
from scipy.stats import linregress
from molass.Geometric.Linesegment import Linesegment, get_segments, plot_segments

XM_POS_SAFE_LIMIT = -3          # > -3.81 for 20200226
XM_POS_LIKE_PH6_LIMIT = -1      # > -1.14 as in pH6

def linregress_segments(segments):
    """Perform linear regression on the center points of the given line segments.

    Parameters
    ----------
    segments : list of Linesegment
        The list of line segments to perform regression on.

    Returns
    -------
    slope : float
        The slope of the fitted line.
    intercept : float
        The intercept of the fitted line.
    """
    xy = np.array([(seg.center_x, seg.center_y) for seg in segments])
    return linregress(*xy.T)[0:2]   # slope, intercept

def reduce_segments(segments, i):
    """Reduce two adjacent line segments into one by merging them.
    
    Parameters
    ----------
    segments : list of Linesegment
        The list of line segments.
    i : int
        The index of the first segment to merge with the next one.
 
    Returns
    -------
    None
        The function modifies the segments list in place.
    """
    segi = segments[i]
    segj = segments[i+1]
    cx = np.concatenate([segi.x, segj.x])
    cy = np.concatenate([segi.y, segj.y])
    cseg = Linesegment(cx, cy)

    segments.pop(i)     # remove i 
    segments.pop(i)     # remove i+1
    segments.insert(i, cseg)

def restore_segments(slope, intercept, segments):
    """Restore the original y-values of the line segments by reversing the linear transformation.

    Parameters
    ----------
    slope : float
        The slope of the linear transformation applied to the y-values.
    intercept : float
        The intercept of the linear transformation applied to the y-values.
    segments : list of Linesegment
        The list of line segments to restore.
    
    Returns
    -------
    list of Linesegment
        The list of restored line segments.
    """
    ret_segments = []
    for seg in segments:
        x = seg.x
        y = seg.y + (x*slope + intercept)
        new_slope = seg.slope + slope
        new_intercept = seg.intercept + intercept
        new_stderr = seg.std_err*new_slope/seg.slope
        ret_segments.append(Linesegment(x, y, regress_info=(new_slope, new_intercept, new_stderr)))
    return ret_segments