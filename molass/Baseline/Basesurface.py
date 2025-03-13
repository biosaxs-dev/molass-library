"""
    Baseline.Basesurface.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from molass.Baseline.Surface import Surface

def get_linear_surface(icurve, jcurve):
    return icurve.y[:,np.newaxis] @ jcurve.y[np.newaxis,:]
