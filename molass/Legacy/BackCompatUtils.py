"""
    Legacy.BackCompatUtils.py

    Copyright (c) 2018-2024, SAXS Team, KEK-PF
"""
import numpy as np

class ElutioCurvProxy:
    def __init__(self, icurve):
        self.x = icurve.x
        self.y = icurve.y
    
    def get_primarypeak_i(self):
        return np.argmax(self.y)