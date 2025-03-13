"""
    Geometric.Linesegment.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.stats import linregress
import ruptures as rpt

class Linesegment:
    def __init__(self, x, y, regress_info=None):
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
        return self.std_err
    
    def get_y(self):
        return self.y
    
    def __neg__(self):
        return Linesegment(self.x, -self.y, regress_info=(-self.slope, -self.intercept, self.std_err))

def get_segments(x, y, breakpoints=None, n_bkps=2):
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
    if ax is None:
        import matplotlib.pyplot as plt 
        fig, ax = plt.subplots()
    if title is not None:
        ax.set_title(title)
    ax.plot(x, y)
    for seg in segments:
        ax.plot(seg.x[[0,-1]], seg.y[[0,-1]], 'o:', lw=2)

def to_negative_segments(segments):
    ret_segments = []
    for seg in segments:
        ret_segments.append(-seg)
    return ret_segments