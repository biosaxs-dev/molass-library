"""
Baseline.IntegralBaseline.py
"""
from molass_legacy.Baseline.Baseline import compute_baseline

def compute_integral_baseline(x, y, kwargs={}):
    return_also_params = kwargs.get('return_also_params', False)
    baseline = compute_baseline(y, x=x, integral=True)
    if return_also_params:
        return baseline, dict()
    else:
        return baseline