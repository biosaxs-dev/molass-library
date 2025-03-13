"""
    Baseline.LpmBaseline2D.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from molass_legacy.Baseline.ScatteringBaseline import ScatteringBaseline

def individual_axes_impl(self, data, axes, method, method_kwargs):
    """Implementation of the LPM baseline fitting for 2D data"""

    from collections import defaultdict
    from functools import partial
    from pybaselines.two_d.optimizers import _check_scalar, _update_params

    assert method == 'molass_lpm'
    moment = method_kwargs.get('moment')
    percent = moment.get_lpm_percent()

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
    baseline = np.zeros(self._len)
    params = {}
    for i, axis in enumerate(axes):
        params[f'params_{keys[axis]}'] = defaultdict(list)
        func = partial(
            _update_params, _lpm_baseline_func, params[f'params_{keys[axis]}'], **method_kwargs[i]
        )
        partial_baseline = np.apply_along_axis(func, axis, data - baseline)
        baseline += partial_baseline
        params[f'baseline_{keys[axis]}'] = partial_baseline

    return baseline, params

def _lpm_baseline_func(data, **kwargs):
    sbl = ScatteringBaseline(data, suppress_warning=True)
    slope, intercept = sbl.solve()
    x = kwargs.get('x', None)
    if x is None:
        x = sbl.x
    baseline = x*slope + intercept
    return baseline, dict(slope=slope, intercept=intercept)