"""
    Baseline.LpmBaseline.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.DataObjects.Curve import Curve

def estimate_lpm_percent(moment):
    M, std = moment.get_meanstd()
    x = moment.x
    ratio = len(np.where(np.logical_or(x < M - 3*std, M + 3*std < x))[0])/len(x)
    return ratio/2

class LpmBaseline(Curve):
    def __init__(self, icurve):
        from Baseline.ScatteringBaseline import ScatteringBaseline
        sbl = ScatteringBaseline(icurve.y, suppress_warning=True)
        A, B = sbl.solve()
        x = icurve.x
        y = x*A + B
        super().__init__(x, y)