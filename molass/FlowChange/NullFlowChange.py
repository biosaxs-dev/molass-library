"""
FlowChange.NullFlowChange.py
"""
import numpy as np
from scipy.stats import linregress

class CsProxy:
    def __init__(self, slope, intercept, a_curve=None, x_curve=None):
        self.slope = slope
        self.intercept = intercept
        self.a_curve = a_curve
        self.x_curve = x_curve
        self.mapped_info = None

    def compute_whole_similarity(self):
        # set the highest similarity to avoid reconstructing Cs
        return 1.0

    def get_mapped_info(self):
        if self.mapped_info is None:
            # task: consider moving this to __init__ and improve mapping if necessary
            from Mapping.PeakMapper import PeakMapper
            pm = PeakMapper(self.a_curve, self.x_curve)
            self.mapped_info = pm.mapped_info
        return self.mapped_info

class NullFlowChange:
    def __init__(self, a_curve, a_curve2, x_curve):
        self.a_curve = a_curve
        self.a_curve2 = a_curve2
        self.x_curve = x_curve
        self.cs = None

    def get_similarity(self):
        if self.cs is None:
            X = self.x_curve.x[[0,-1]]
            Y = self.a_curve.x[[0,-1]]
            slope, intercept = linregress(X, Y)[0:2]
            self.cs = CsProxy(slope, intercept, a_curve=self.a_curve, x_curve=self.x_curve)
        return self.cs

    def get_real_flow_changes(self):
        return None, None
    
    def has_special(self):
        return False
    
    def remove_irregular_points(self):
        return np.array([]), np.array([]), slice(None, None)