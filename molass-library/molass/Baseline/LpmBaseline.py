"""
    Baseline.LpmBaseline.py
"""
import numpy as np
from scipy import stats
from molass.DataObjects.Curve import Curve
from molass_legacy.Baseline.ScatteringBaseline import ScatteringBaseline

def estimate_lpm_percent(moment):
    """Estimate the percentage of low-q plateau in the distribution using the moment.

    Parameters
    ----------
    moment : Moment
        The moment object containing the distribution information.  

    Returns
    -------
    ratio : float
        The estimated percentage of low-q plateau in the distribution.
    """
    M, std = moment.get_meanstd()
    x = moment.x
    ratio = len(np.where(np.logical_or(x < M - 3*std, M + 3*std < x))[0])/len(x)
    return ratio/2

def _compute_adaptive_p_final(x, y, size_sigma):
    """Compute adaptive p_final from per-row noisiness, replicating legacy behaviour."""
    from scipy.interpolate import LSQUnivariateSpline
    from molass_legacy.SerialAnalyzer.BasePercentileOffset import base_percentile_offset
    n = len(y)
    knots = np.linspace(x[0], x[-1], max(3, n // 10) + 2)[1:-1]
    try:
        spline = LSQUnivariateSpline(x, y, knots)
        noisiness = np.std(y - spline(x))
        signal_scale = max(np.abs(y).max(), 1e-12)
        noisiness = noisiness / signal_scale  # relative noisiness, matching table calibration
    except Exception:
        noisiness = np.std(y)
    return base_percentile_offset(noisiness, size_sigma=size_sigma)


def compute_lpm_baseline(x, y, return_also_params=False, **kwargs):
    """Compute the linear plus minimum baseline for a given curve.
    The baseline is computed by fitting a linear function to the data and then taking the minimum of the linear function and the data.
    
    Parameters
    ----------
    x : array-like
        The x-coordinates of the curve.
    y : array-like
        The y-coordinates of the curve.
    return_also_params : bool, optional
        If True, the function returns a tuple containing the baseline and a dictionary of the slope and intercept of the linear function.
        If False, it returns only the baseline.
    **kwargs : dict, optional
        Additional keyword arguments.

        - ``size_sigma`` : float — if present, an adaptive ``p_final`` is
          computed per-row (replicating legacy behaviour); otherwise the
          default ``PERCENTILE_FINAL=10`` is used.
        - ``mask`` : array-like of bool — if present, only the elements where
          ``mask`` is True are used for fitting.  The returned baseline is
          evaluated at **all** ``x`` positions.
        - ``endpoint_fraction`` : float — if present and > 0, switches to
          **endpoint-anchored** mode: the anchor set is the leading and
          trailing ``k = max(2, int(endpoint_fraction * n))`` frames.
          Intended for datasets with physically real negative peaks where the
          standard low-percentile anchor would be contaminated.  The standard
          LPM path is taken when this is ``None`` (default).

    Returns
    -------
    baseline : array-like
        The computed baseline.
    """
    endpoint_fraction = kwargs.get('endpoint_fraction', None)
    if endpoint_fraction is not None and endpoint_fraction > 0:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        n = len(x)
        k = max(2, int(endpoint_fraction * n))
        ep_mask = np.zeros(n, dtype=bool)
        ep_mask[:k] = True
        ep_mask[-k:] = True
        slope, intercept, *_ = stats.linregress(x[ep_mask], y[ep_mask])
        baseline = slope * x + intercept
        if return_also_params:
            return baseline, dict(slope=slope, intercept=intercept, p_final=None,
                                  endpoint_fraction=endpoint_fraction)
        return baseline

    mask = kwargs.get('mask', None)

    if mask is not None:
        x_fit = x[mask]
        y_fit = y[mask]
    else:
        x_fit = x
        y_fit = y

    size_sigma = kwargs.get('size_sigma', None)
    if size_sigma is not None and x_fit is not None:
        p_final = _compute_adaptive_p_final(x_fit, y_fit, size_sigma)
    else:
        p_final = None  # use ScatteringBaseline default (PERCENTILE_FINAL=10)

    sbl = ScatteringBaseline(y_fit, x=x_fit)
    solve_kwargs = {} if p_final is None else {'p_final': p_final}
    slope, intercept = sbl.solve(**solve_kwargs)
    baseline = x*slope + intercept
    if return_also_params:
        return baseline, dict(slope=slope, intercept=intercept, p_final=p_final)
    else:
        return baseline


class LpmBaseline(Curve):
    """A class to represent the linear plus minimum baseline of a curve.
    
    Attributes
    ----------
    x : array-like
        The x-coordinates of the baseline.
    y : array-like
        The y-coordinates of the baseline.
    """
    def __init__(self, icurve):
        x = icurve.x
        y = compute_lpm_baseline(x, icurve.y)
        super().__init__(x, y)