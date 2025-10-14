"""
    Baseline.LpmBaseline.py
"""
import numpy as np
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
        Additional keyword arguments to pass to the ScatteringBaseline solver.

    Returns
    -------
    baseline : array-like
        The computed baseline.
    """
    sbl = ScatteringBaseline(y, x=x)
    slope, intercept = sbl.solve()
    baseline = x*slope + intercept
    if return_also_params:
        return baseline, dict(slope=slope, intercept=intercept)
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