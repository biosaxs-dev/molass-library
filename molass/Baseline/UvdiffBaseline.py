"""
Baseline.UvdifflBaseline.py
"""
from molass.Baseline.UvBaseline import estimate_uvbaseline_params
from molass.Baseline.LpmBaseline import compute_lpm_baseline

def get_uvdiff_baseline_info(uv_data, pickat=400):
    """
    Get the parameters and baseline for UVDIFF baseline fitting.

    Note that, in 2D cases, this function is called only once instead of every
    call to the baseline computation.
    """
    c1 = uv_data.get_icurve()
    c2 = uv_data.get_icurve(pickat=pickat)
    params, dy, uvdiff_baseline = estimate_uvbaseline_params(c1, c2, pickat=pickat, return_also_baseline=True)
    return params, dy, uvdiff_baseline

def compute_uvdiff_baseline(x, y, kwargs):
    uvdiff_info = kwargs.get('uvdiff_info', None)
    if uvdiff_info is None:
        raise ValueError("uvdiff_info must be provided in kwargs")

    # note that uvdiff_info is the return value from get_uvdiff_baseline_info
    params, dy, uvdiff_baseline = uvdiff_info

    lpm_baseline = compute_lpm_baseline(x, y, {})  # Ensure LPM baseline is computed if needed
    return_also_params = kwargs.get('return_also_params', False)
    ret_baseline = lpm_baseline + uvdiff_baseline
    if return_also_params:
        return ret_baseline, dict(params=params)
    else:
        return ret_baseline