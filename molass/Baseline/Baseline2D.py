"""
    Baseline.Baseline2D.py
"""
import numpy as np
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from pybaselines import Baseline2D as _Baseline2D
from importlib import reload

def individual_axes_impl(self, data, axes, method, method_kwargs, baseline_func):
    """
    Implementation of the LPM baseline fitting for 2D data

    This is overriding the implementation in
    pybaselines.two_d.optimizers._Optimizers.individual_axes
    """

    from collections import defaultdict
    from functools import partial
    from pybaselines.two_d.optimizers import _check_scalar, _update_params

    assert method in ['linear', 'uvdiff', 'integral']

    axes, scalar_axes = _check_scalar(axes, 2, fill_scalar=False, dtype=int)
    if scalar_axes:
        axes = [axes]
        num_axes = 1
    else:
        if axes[0] == axes[1]:
            raise ValueError('Fitting the same axis twice is not allowed')
        num_axes = 2
    if (
        method_kwargs is None
        or (not isinstance(method_kwargs, dict) and len(method_kwargs) == 0)
    ):
        method_kwargs = [{}] * num_axes
    elif isinstance(method_kwargs, dict):
        method_kwargs = [method_kwargs] * num_axes
    elif len(method_kwargs) == 1:
        method_kwargs = [method_kwargs[0]] * num_axes
    elif len(method_kwargs) != num_axes:
        raise ValueError('Method kwargs must have the same length as the input axes')

    keys = ('rows', 'columns')
    baseline = np.zeros(self._shape)
    params = {}
    for i, axis in enumerate(axes):
        params[f'params_{keys[axis]}'] = defaultdict(list)
        func = partial(
            _update_params, baseline_func, params[f'params_{keys[axis]}'], **method_kwargs[i]
        )
        partial_baseline = np.apply_along_axis(func, axis, data - baseline)
        baseline += partial_baseline
        params[f'baseline_{keys[axis]}'] = partial_baseline

    return baseline, params

def _lpm_individual_axes_impl(self, data, axes, method, method_kwargs, debug=False):
    """
    Adapter for LPM baseline fitting
    """
    from molass.Baseline.LpmBaseline import compute_lpm_baseline
    def _lpm_baseline_func(data, **kwargs):
        if debug:
            counter = kwargs.get('counter', None)
            if counter is not None:
                counter[0] += 1
        x = kwargs.get('jv', None)
        return compute_lpm_baseline(x, data, return_also_params=True, **kwargs)
    
    return individual_axes_impl(self, data, axes, method, method_kwargs, _lpm_baseline_func)

def _uvdiff_individual_axes_impl(self, data, axes, method, method_kwargs, debug=False):
    """
    Adapter for UVDIFF baseline fitting
    """
    from molass.Baseline.UvdiffBaseline import compute_uvdiff_baseline
    def _uvdiff_baseline_func(data, **kwargs):
        if debug:
            counter = kwargs.get('counter', None)
            if counter is not None:
                counter[1] += 1
        x = kwargs.get('jv', None)
        uvdiff_info=kwargs.get('uvdiff_info', None)
        return compute_uvdiff_baseline(x, data, uvdiff_info, return_also_params=True)

    return individual_axes_impl(self, data, axes, method, method_kwargs, _uvdiff_baseline_func)

def _integral_individual_axes_impl(self, data, axes, method, method_kwargs, debug=False):
    """
    Adapter for INTEGRAL baseline fitting
    """
    from molass.Baseline.IntegralBaseline import compute_integral_baseline
    def _integral_baseline_func(data, **kwargs):
        if debug:
            counter = kwargs.get('counter', None)
            if counter is not None:
                counter[2] += 1
        x = kwargs.get('jv', None)  # but not used in this case
        return compute_integral_baseline(x, data, return_also_params=True)

    return individual_axes_impl(self, data, axes, method, method_kwargs, _integral_baseline_func)

CUSTOM_IMPL_DICT = {
    'linear': _lpm_individual_axes_impl,
    'uvdiff': _uvdiff_individual_axes_impl,
    'integral': _integral_individual_axes_impl
}

class Baseline2D(_Baseline2D):
    """A LPM-specialized class for 2D baseline fitting"""

    def __init__(self, x, y):
        """Same as the parent class"""
        super().__init__(x, y)

    def individual_axes(self, data, axes=(0, 1), method='asls', method_kwargs=None, debug=True):
        """Override the method to use custom baseline fitting"""
        custom_impl = CUSTOM_IMPL_DICT.get(method, None)
        if custom_impl is None:
            super().individual_axes(data, axes, method, method_kwargs)
        else:
            return custom_impl(self, data, axes, method, method_kwargs, debug=debug)