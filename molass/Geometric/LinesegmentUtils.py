"""
    Geometric.LinesegmentUtils.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.stats import linregress
from molass.Geometric.Linesegment import Linesegment, get_segments, plot_segments

XM_POS_SAFE_LIMIT = -3          # > -3.81 for 20200226
XM_POS_LIKE_PH6_LIMIT = -1      # > -1.14 as in pH6

def linregress_segments(segments):
    xy = np.array([(seg.center_x, seg.center_y) for seg in segments])
    return linregress(*xy.T)[0:2]   # slope, intercept

def reduce_segments(segments, i):
    segi = segments[i]
    segj = segments[i+1]
    cx = np.concatenate([segi.x, segj.x])
    cy = np.concatenate([segi.y, segj.y])
    cseg = Linesegment(cx, cy)

    segments.pop(i)     # remove i 
    segments.pop(i)     # remove i+1
    segments.insert(i, cseg)

def restore_segments(slope, intercept, segments):
    ret_segments = []
    for seg in segments:
        x = seg.x
        y = seg.y + (x*slope + intercept)
        new_slope = seg.slope + slope
        new_intercept = seg.intercept + intercept
        new_stderr = seg.std_err*new_slope/seg.slope
        ret_segments.append(Linesegment(x, y, regress_info=(new_slope, new_intercept, new_stderr)))
    return ret_segments