"""
    Baseline.BaselineUtils.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from pybaselines import Baseline
from molass.Global.Options import get_molass_options

def pybaselines_asls_impl(x, y, kwargs):
    baseline_fitter = Baseline(x_data=x)
    baseline = baseline_fitter.asls(y, lam=1e7, p=0.02)[0]
    return baseline

def pybaselines_imor_impl(x, y, kwargs):
    baseline_fitter = Baseline(x_data=x)
    baseline = baseline_fitter.imor(y, 10)[0]
    return baseline

def pybaselines_mormol_impl(x, y, kwargs):
    baseline_fitter = Baseline(x_data=x)
    half_window = 100
    baseline = baseline_fitter.mormol(y, half_window, smooth_half_window=10, pad_kwargs={'extrapolate_window': 20})[0]
    return baseline

def molass_lpm_impl(x, y, kwargs):
    from molass_legacy.Baseline.ScatteringBaseline import ScatteringBaseline
    moment = kwargs.get('moment')
    percent = moment.get_lpm_percent()
    sbl = ScatteringBaseline(y, x=x, suppress_warning=True)
    slope, intercept = sbl.solve()
    baseline = x*slope + intercept
    return baseline

METHOD_DICT = {
    'molass_uv': molass_lpm_impl,
    'molass_lpm': molass_lpm_impl,
    'default': ('molass_uv', 'molass_lpm'),
    'asls': pybaselines_asls_impl,
    'imor': pybaselines_imor_impl,
    'mormol': pybaselines_mormol_impl,
}

def iterlen(a):
    if type(a) is str:
        return 1
    try:
        return len(a)
    except:
        return 1

def get_baseline_func(method):
    if method is None:
        method = get_molass_options('baseline_method')

    num_methods = iterlen(method)
    if num_methods == 1:
        if type(method) is str:
            method = METHOD_DICT[method]
        else:
            raise TypeError("given method is not a pair of methods")

    num_methods = iterlen(method)
    if num_methods == 1:
        methods = [method, method]
    elif num_methods == 2:
        methods = method
    else:
        raise TypeError(f"given number of methods {num_methods} != 2")

    ret_methods = []
    for m in methods:
        if type(m) is str:
            func = METHOD_DICT[m]
        elif callable(m):
            func = m
        else:
            raise TypeError(f"method should be either str type, callable, or a pair of those")
        ret_methods.append(func)
    return ret_methods

def get_uv_baseline_func(method):
    return get_baseline_func(method)[0]

def get_xr_baseline_func(method):
    return get_baseline_func(method)[1]