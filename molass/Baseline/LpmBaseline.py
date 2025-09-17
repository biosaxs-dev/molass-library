"""
    Baseline.LpmBaseline.py
"""
import numpy as np
from molass.DataObjects.Curve import Curve
from molass_legacy.Baseline.ScatteringBaseline import ScatteringBaseline

def estimate_lpm_percent(moment):
    M, std = moment.get_meanstd()
    x = moment.x
    ratio = len(np.where(np.logical_or(x < M - 3*std, M + 3*std < x))[0])/len(x)
    return ratio/2

def compute_lpm_baseline(x, y, return_also_params=False, **kwargs):
    sbl = ScatteringBaseline(y, x=x)
    slope, intercept = sbl.solve()
    baseline = x*slope + intercept
    if return_also_params:
        return baseline, dict(slope=slope, intercept=intercept)
    else:
        return baseline
class LpmBaseline(Curve):
    def __init__(self, icurve):
        x = icurve.x
        y = compute_lpm_baseline(x, icurve.y)
        super().__init__(x, y)