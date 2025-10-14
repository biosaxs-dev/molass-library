"""
Baseline.IntegralBaseline.py
"""
import numpy as np
NUM_END_POINTS = 10

def compute_integral_baseline(x, y, start_y=None, final_y=None, return_also_params=False):
    """
    Compute the integral baseline for a given curve.
    The baseline is computed by integrating the curve and scaling it to match the start and end points.

    Parameters
    ----------
    x : array-like
        The x-coordinates of the curve.
    y : array-like
        The y-coordinates of the curve. 
    start_y : float, optional
        The desired value of the baseline at the start of the curve. If None, it is computed as the average of the first NUM_END_POINTS points. 
    final_y : float, optional
        The desired value of the baseline at the end of the curve. If None, it is computed as the average of the last NUM_END_POINTS points.    
    return_also_params : bool, optional
        If True, the function returns a tuple containing the baseline and an empty dictionary. If False, it returns only the baseline.
        
    Returns
    -------
    baseline : array-like
        The computed baseline.
    params : dict, optional
        An empty dictionary if `return_also_params` is True.
    """
    if start_y is None:
        start_y = np.average(y[0:NUM_END_POINTS])

    if final_y is None:
        final_y = np.average(y[-NUM_END_POINTS:])

    cy = np.cumsum(y)
    ratio = (final_y - start_y) / (cy[-1] - cy[0])
    baseline = start_y + (cy - cy[0]) * ratio

    if return_also_params:
        return baseline, dict()
    else:
        return baseline