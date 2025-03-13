"""
    Stats.Moment.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np

def compute_meanstd(x, y):
    W = np.sum(y)
    M1 = np.sum(x*y)/W              # raw moment
    M2 = np.sum(y*(x-M1)**2)/W      # central moment
    return M1, np.sqrt(M2)

class Moment:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.y_ = None
        self.M = None       # to avoid repeated computation in case with multiple references
        self.std = None
        self.lpm_percent = None
    
    def get_y_(self, **kwargs):
        if self.y_ is None:
            y_ = self.y.copy()
            y_[y_ < 0] = 0  # negative values are usually inappropriate for weights
            self.y_ = y_
        return self.y_
    
    def get_meanstd(self):
        if self.y_ is None:
            y_ = self.get_y_()
            self.M, self.std = compute_meanstd(self.x, y_)
        return self.M, self.std
    
    def is_in_nsigma(self, n, px):
        M, std = self.get_meanstd()
        return M - n*std < px and px < M + n*std
    
    def get_nsigma_points(self, n):
        M, std = self.get_meanstd()
        wanted_range = np.logical_and(M - n*std < self.x, self.x < M + n*std)
        i, j = np.where(wanted_range)[0][[0,-1]]
        return i, j
    
    def get_lpm_percent(self, debug=True):
        if self.lpm_percent is None or debug:
            if debug:
                from importlib import reload
                import molass.Baseline.LpmBaseline
                reload(molass.Baseline.LpmBaseline)
            from molass.Baseline.LpmBaseline import estimate_lpm_percent
            self.lpm_percent = estimate_lpm_percent(self)
        return self.lpm_percent