"""
Bridge.SdProxy.py
"""
import numpy as np
from bisect import bisect_right
from molass.DataObjects.XrData import PICKAT
from molass_legacy.SerialAnalyzer.ElutionCurve import ElutionCurve
from molass_legacy.SecSaxs.ElCurve import ElCurve

def _resolve_neg_peak_exclude(xr):
    """Return a bool array (len = num frames) where True = exclude from LPM anchors.

    Mirrors the same logic as SsMatrixData.get_baseline2d() so that the
    ScatteringBaseline in the rigorous path skips the same frames that the
    standard corrected_copy() path skips.
    """
    if not getattr(xr, 'allow_negative_peaks', False):
        return None
    np_mask = getattr(xr, 'negative_peak_mask', None)
    jv = xr.jv
    if np_mask is None:
        rc_y = xr.get_recognition_curve().y
        return rc_y < 0
    elif isinstance(np_mask, slice):
        i_start = np.searchsorted(jv, np_mask.start) if np_mask.start is not None else None
        i_stop  = np.searchsorted(jv, np_mask.stop, side='right') if np_mask.stop is not None else None
        exclude = np.zeros(len(jv), dtype=bool)
        exclude[slice(i_start, i_stop)] = True
        return exclude
    else:
        return np.asarray(np_mask, dtype=bool)


class AbsorbanceProxy:
    def __init__(self, ssd):
        if ssd.uv is None:
            # temporary work-around for the case without UV data 
            uv = ssd.xr
            self.wl_vector = uv.qv
        else:
            uv = ssd.uv
            self.wl_vector = uv.wv
        self.data = uv.M
        self.icurve = uv.get_icurve()
        self.a_curve = ElutionCurve(self.icurve.y)
        self.a_vector = self.icurve.y

class EcurveProxy(ElCurve):
    def __init__(self, curve):
        x = curve.x
        y = curve.y
        # Use 0-based ElutionCurve to avoid frame-number / array-index mismatch
        v1 = ElutionCurve(y)
        super().__init__(x, y, v1_curve=v1)
        self.height = np.max(y)

class SdProxy:
    def __init__(self, ssd, pre_recog=None):
        self.ssd = ssd
        self.pre_recog = pre_recog
        self.intensity_array = self.get_intensity_array_top()
        self.xr_curve = None
        self.xray_curve = None
        self.uv_curve = None
        self.absorbance = AbsorbanceProxy(ssd)
        if ssd.uv is None:
            # temporary work-around for the case without UV data
            self.conc_array = ssd.xr.M
            self.lvector = ssd.xr.qv
        else:
            self.conc_array = ssd.uv.M
            self.lvector = ssd.uv.wv
        self.xr_index = bisect_right(ssd.xr.qv, PICKAT)
        self.xray_index = self.xr_index
        self.mtd_elution = None
    
    def get_copy(self, pre_recog=None):
        return SdProxy(self.ssd, pre_recog=pre_recog)

    def get_intensity_array_top(self):
        xr = self.ssd.xr
        X = xr.M
        E = xr.E
        qv = xr.qv
        return np.array([np.array([qv, X[:,0], E[:,0]]).T])

    def get_xr_curve(self):
        if self.xr_curve is None:
            # Use get_recognition_curve() so that the global elution_recognition
            # option ('icurve' or 'sum') propagates into the legacy baseline
            # computation.  When 'icurve' (default), this returns get_icurve()
            # unchanged; when 'sum', it returns M.sum(axis=0).
            recog = self.ssd.xr.get_recognition_curve()
            # Normalize to icurve scale: preserves the shape advantage of sum
            # recognition for LPM while keeping magnitude compatible with the
            # per-q optimizer (EGH components are at per-q scale).
            icurve = self.ssd.xr.get_icurve()
            max_r = np.max(recog.y)
            max_i = np.max(icurve.y)
            y = recog.y.copy()
            if max_r > 0 and max_i > 0 and abs(max_r - max_i) / max_r > 1e-6:
                y = y * (max_i / max_r)
            # Propagate allow_negative_peaks: replace excluded frames with max(y)
            # so ScatteringBaseline's percentile logic treats them as high-signal
            # (not buffer) and skips them as anchor candidates.
            exclude = _resolve_neg_peak_exclude(self.ssd.xr)
            if exclude is not None and exclude.any():
                y = y.copy()
                y[exclude] = np.max(y)
            from molass.DataObjects.Curve import Curve
            self.xr_curve = EcurveProxy(Curve(recog.x, y))
            self.xray_curve = self.xr_curve
        return self.xr_curve

    def get_xr_data_separate_ly(self):
        xr = self.ssd.xr
        X = xr.M
        E = xr.E
        qv = xr.qv
        xr_curve = self.get_xr_curve()
        return X, E, qv, xr_curve

    def get_uv_curve(self):
        if self.uv_curve is None:
            if self.ssd.uv is None:
                # temporary work-around for the case without UV data
                self.uv_curve = self.get_xr_curve()
            else:
                self.uv_curve = EcurveProxy(self.ssd.uv.get_icurve())
        return self.uv_curve

    def get_uv_data_separate_ly(self):
        if self.ssd.uv is None:
            # temporary work-around for the case without UV data
            U, _, wv, uv_curve = self.get_xr_data_separate_ly()
        else:
            uv = self.ssd.uv
            U = uv.M
            wv = uv.wv
            uv_curve = self.get_uv_curve()
        return U, None, wv, uv_curve