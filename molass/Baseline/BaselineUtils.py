"""
    Baseline.BaselineUtils.py
"""
from importlib import reload
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from pybaselines import Baseline

def molass_lpm_impl(x, y, **kwargs):
    """Linear plus minimum baseline implementation.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    kwargs : dict
        Additional keyword arguments to pass to the baseline computation function.

    Returns
    -------
    baseline : array-like
        The computed baseline values.
    """
    from molass.Baseline.LpmBaseline import compute_lpm_baseline
    return compute_lpm_baseline(x, y, **kwargs)

def molass_uvdiff_impl(x, y, **kwargs):
    """UV difference baseline implementation.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    kwargs : dict
        Additional keyword arguments to pass to the baseline computation function.

    Returns
    -------
    baseline : array-like
        The computed baseline values.
    """
    import molass.Baseline.UvdiffBaseline
    reload(molass.Baseline.UvdiffBaseline)  
    from molass.Baseline.UvdiffBaseline import compute_uvdiff_baseline
    return compute_uvdiff_baseline(x, y, **kwargs)

def molass_integral_impl(x, y, **kwargs):
    """Integral baseline implementation.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    kwargs : dict
        Additional keyword arguments to pass to the baseline computation function.

    Returns
    -------
    baseline : array-like
        The computed baseline values.
    """
    from molass.Baseline.IntegralBaseline import compute_integral_baseline
    return compute_integral_baseline(x, y)

def pybaselines_asls_impl(x, y, **kwargs):
    """Asymmetric least squares baseline implementation using pybaselines.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    kwargs : dict
        Additional keyword arguments to pass to the baseline computation function.

    Returns
    -------
    baseline : array-like
        The computed baseline values.
    """
    baseline_fitter = Baseline(x_data=x)
    baseline = baseline_fitter.asls(y, lam=1e7, p=0.02)[0]
    return baseline

def pybaselines_imor_impl(x, y, **kwargs):
    """Improved modified polynomial fitting baseline implementation using pybaselines.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    kwargs : dict
        Additional keyword arguments to pass to the baseline computation function.

    Returns
    -------
    baseline : array-like
        The computed baseline values.
    """
    baseline_fitter = Baseline(x_data=x)
    baseline = baseline_fitter.imor(y, 10)[0]
    return baseline

def pybaselines_mormol_impl(x, y, **kwargs):
    """Morphological operations baseline implementation using pybaselines.
    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    kwargs : dict
        Additional keyword arguments to pass to the baseline computation function.
    Returns
    -------
    baseline : array-like
        The computed baseline values.
    """
    baseline_fitter = Baseline(x_data=x)
    half_window = 100
    baseline = baseline_fitter.mormol(y, half_window, smooth_half_window=10, pad_kwargs={'extrapolate_window': 20})[0]
    return baseline

METHOD_DICT = {
    'linear': molass_lpm_impl,
    'uvdiff': molass_uvdiff_impl,
    'integral': molass_integral_impl,
    'asls': pybaselines_asls_impl,
    'imor': pybaselines_imor_impl,
    'mormol': pybaselines_mormol_impl,
}

def iterlen(a):
    """Get the length of an iterable, or 1 if it is not iterable.

    Parameters
    ----------
    a : any
        The object to check.

    Returns
    -------
    length : int
        The length of the iterable, or 1 if it is not iterable.
    """
    if type(a) is str:
        return 1
    try:
        return len(a)
    except:
        return 1

def get_baseline_func(method):
    """Get the baseline function(s) corresponding to the given method(s).

    Parameters
    ----------
    method : str, callable, or list/tuple of str/callable
        The method(s) to get the baseline function(s) for.
        If a single method is given, it will be used for both UV and XR baselines.
        If a list or tuple of two methods is given, the first will be used for UV and the second for XR.
        Each method can be either a string (key in METHOD_DICT) or a callable (custom function).

    Returns
    -------
    functions : list of callables
        A list containing the baseline function for UV and XR, respectively.
    """
    if method is None:
        method = 'linear'
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
    """Get the UV baseline function corresponding to the given method.

    Parameters
    ----------
    method : str, callable, or list/tuple of str/callable
        The method(s) to get the baseline function(s) for.
        If a single method is given, it will be used for both UV and XR baselines.
        If a list or tuple of two methods is given, the first will be used for UV and the second for XR.
        Each method can be either a string (key in METHOD_DICT) or a callable (custom function).

    Returns
    -------
    function : callable
        The baseline function for UV.
    """
    return get_baseline_func(method)[0]

def get_xr_baseline_func(method):
    """Get the XR baseline function corresponding to the given method.
    
    Parameters
    ----------
    method : str, callable, or list/tuple of str/callable
        The method(s) to get the baseline function(s) for.
        If a single method is given, it will be used for both UV and XR baselines.
        If a list or tuple of two methods is given, the first will be used for UV and the second for XR.
        Each method can be either a string (key in METHOD_DICT) or a callable (custom function).

    Returns
    -------
    function : callable
        The baseline function for XR.
    """
    return get_baseline_func(method)[1]