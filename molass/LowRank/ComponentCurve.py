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