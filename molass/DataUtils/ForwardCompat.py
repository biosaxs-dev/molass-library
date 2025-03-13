"""
DataUtils.ForwardCompat.py

This module is used to convert old data objects to new ones.
"""
import numpy as np
from scipy.stats import linregress
from scipy.interpolate import UnivariateSpline
from molass.FlowChange.NullFlowChange import CsProxy, NullFlowChange

class CurveProxy:
    def __init__(self, x, y, peak_info):
        self.x = x
        self.y = y
        self.spline = UnivariateSpline(x, y, s=0, ext=3)
        self.peak_info = peak_info

class PreRecogProxy:
    def __init__(self, flowchange, cs):
        self.flowchange = flowchange
        self.cs = cs

def get_start_index(slice_):
    j = slice_.start
    if j is None:
        j = 0
    return j

def get_trimmed_curve(curve, slice_, renumber=True, convert_peak_info=True):
    size = slice_.stop
    if size is None:
        size = len(curve.x)
    j = get_start_index(slice_)
    x, y = curve.get_xy()
    if renumber:
        x_ = np.arange(size - j)
    else:
        x_ = x[slice_]
    y_ = y[slice_]
    if convert_peak_info:
        new_peak_info = []
        for rec in curve.peak_info:
            new_peak_info.append([n - j for n in rec])
    else:
        new_peak_info = None
    return CurveProxy(x_, y_, new_peak_info)

def convert_to_trimmed_prerecog(pre_recog, uv_restrict_list, xr_restrict_list, renumber=True, debug=False):
    if debug:
        print("convert_to_trimmed_prerecog")
        print("uv_restrict_list=", uv_restrict_list)
        print("xr_restrict_list=", xr_restrict_list)
    
    fc = pre_recog.flowchange

    uv_slice = uv_restrict_list[0].get_slice()
    trimmed_uv_curves = []
    for k, curve in enumerate([fc.a_curve, fc.a_curve2]):
        trimmed_uv_curves.append(get_trimmed_curve(curve, uv_slice, renumber=renumber, convert_peak_info=k == 0))

    xr_slice = xr_restrict_list[0].get_slice()
    old_cs = pre_recog.cs
    trimmed_xr_curve = get_trimmed_curve(old_cs.x_curve, xr_slice, renumber=renumber)

    xr_x = old_cs.x_curve.x
    uv_x = fc.a_curve.x
    X = xr_x[[0,-1]]
    slope = old_cs.slope
    intercept = old_cs.intercept
    Y = slope * X + intercept
    i = get_start_index(xr_slice)
    j = get_start_index(uv_slice)
    X_ = X - xr_x[i]
    Y_ = Y - uv_x[j]
    slope_, intercept_ = linregress(X_, Y_)[0:2]
    new_cs = CsProxy(slope_, intercept_)

    return PreRecogProxy(NullFlowChange(*trimmed_uv_curves, trimmed_xr_curve), new_cs)
