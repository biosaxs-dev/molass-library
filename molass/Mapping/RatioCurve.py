"""
    Mapping.RatioCurve.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np

def compute_ratio_curve(x, y1, y2, smoothig=True, ignore_height=None): 
    from molass.DataObjects.Curve import Curve
    from KekLib.SciPyCookbook import smooth
 
    if smoothig:
        y1 = smooth(y1)
        y2 = smooth(y2)
    
    if ignore_height is None:
        ignore_height = np.max(y2)*0.05
        
    ratio = y1/y2
    invalid = np.logical_or(y1 < 0, y2 < ignore_height)
    ratio[invalid] = np.nan
    return Curve(x, ratio)