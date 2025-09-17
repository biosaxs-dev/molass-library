"""
    Stats.EghMoment.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
from .Moment import Moment, compute_meanstd
from molass.LowRank.CurveDecomposer import decompose_icurve_impl

class EghMoment(Moment):
    def __init__(self, icurve, num_peaks=None):
        super().__init__(icurve.x, icurve.y)
        self.icurve = icurve
        self.num_peaks = num_peaks

    def get_y_(self):
        if self.y_ is None:
            self.y_ = self.compute_egh_y()
        return self.y_

    def compute_egh_y(self):
        icurve = self.icurve
        if self.num_peaks is None:
            self.num_peaks = len(icurve.get_peaks())
        self.curves = decompose_icurve_impl(icurve, self.num_peaks)   # egh component
        cy_list = []
        for curve in self.curves:
            _, cy = curve.get_xy()
            cy_list.append(cy)
        ty = np.sum(cy_list, axis=0)
        return ty
        