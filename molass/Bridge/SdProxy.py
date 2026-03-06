"""
Bridge.SdProxy.py
"""
import numpy as np
from bisect import bisect_right
from molass.DataObjects.XrData import PICKAT
from molass_legacy.SerialAnalyzer.ElutionCurve import ElutionCurve
from molass_legacy.SecSaxs.ElCurve import ElCurve

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
        super().__init__(x, y)
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
            self.xr_curve = EcurveProxy(self.ssd.xr.get_icurve())
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