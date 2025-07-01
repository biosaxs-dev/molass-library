"""
Baseline.IntegralBaseline.py
"""
from molass_legacy.Baseline.Baseline import compute_baseline

def compute_integral_baseline(x, y):
    return compute_baseline(y, x=x, integral=True)