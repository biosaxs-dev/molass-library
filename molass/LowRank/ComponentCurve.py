"""
    LowRank.ComponentCurve.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass_legacy.Models.ElutionCurveModels import egh

class ComponentCurve:
    """
    A class to represent a component curve.
    """

    def __init__(self, x, params):
        """
        """
        self.x = x
        self.params = np.asarray(params)
    
    def get_xy(self):
        """
        """
        x = self.x
        return x, egh(x, *self.params)
    
    def get_peak_top_x(self):
        """
        Returns the x value at the peak top.
        """
        return self.params[1]   # peak position in EGH model, note that this in valid only for EGH model