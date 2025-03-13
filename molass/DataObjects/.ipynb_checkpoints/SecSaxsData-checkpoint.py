"""
    DataObject.SecSaxsData.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from glob import glob

class SecSaxsData:
    def __init__(self, folder):
        data_list = []
        for path in glob(folder + "/*.dat"):
            data_list.append(np.loadtxt(path))
        self.xr_data = np.array(data_list)
        self.num_files = len(data_list)
        self.xr_curve = None
        self.qvector = self.xr_data[0,:,0]

        from molass_legacy.SerialAnalyzer.SerialDataUtils import load_uv_array
        data_array, lvector, conc_file = load_uv_array(folder)
        self.uv_data = data_array.T
        self.uv_curve = None
        self.wvector = lvector

    def get_xr_curve(self):
        if self.xr_curve is None:
            from molass.DataObjects.ElutionCurve import create_xr_curve
            self.xr_curve = create_xr_curve(self.qvector, self.xr_data)
        return self.xr_curve

    def get_uv_curve(self):
        if self.uv_curve is None:
            from molass.DataObjects.ElutionCurve import create_uv_curve
            self.uv_curve = create_uv_curve(self.wvector, self.uv_data)
        return self.uv_curve