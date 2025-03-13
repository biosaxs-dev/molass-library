"""
    DataObject.ElutionCurve.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from bisect import bisect_right

class ElutionCurve:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def create_xr_curve(qvector, data):
    x = np.arange(data.shape[0])
    i = bisect_right(qvector, 0.02)
    y = data[:,i,1]
    return ElutionCurve(x, y)

def create_uv_curve(wvector, data):
    x = np.arange(data.shape[0])
    i = bisect_right(wvector, 280)
    print(wvector[[0,-1]], data.shape, i)
    y = data[:,i]
    return ElutionCurve(x, y)