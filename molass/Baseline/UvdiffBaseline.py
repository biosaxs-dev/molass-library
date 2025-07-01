"""
Baseline.UvdifflBaseline.py
"""
from molass.Baseline.UvBaseline import estimate_uvbaseline_params
from molass.Baseline.LpmBaseline import compute_lpm_baseline

def compute_uvdiff_baseline(x, y, kwargs):
    uv_data = kwargs.get('uv_data', None)
    if uv_data is None:
        raise ValueError("uv_data must be provided in kwargs")

    lpm_baseline = compute_lpm_baseline(x, y, {})  # Ensure LPM baseline is computed if needed

    c1 = uv_data.get_icurve()
    pickat = kwargs.get('pickat', 400)
    c2 = uv_data.get_icurve(pickat=pickat)
    params, dy, uvdiff_baseline = estimate_uvbaseline_params(c1, c2, pickat=pickat, return_also_baseline=True)
    return lpm_baseline + uvdiff_baseline