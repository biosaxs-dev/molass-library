"""
Backward.SerialData.py
"""
import numpy as np
class PreRecogProxy:
    """
    A proxy class for the pre-recognition data.
    This class is used to hold the pre-recognition data for serial processing.
    """
    def __init__(self, ssd):
        pass

    def get_rg(self):
        """
        Returns the radius of gyration.
        """
        return None


def convert_to_intensity_array(qv, M, E):
    """
    Convert the X-ray data to an intensity array.
    This function extracts the q, I, and sigq values from the XR data.
    """
    assert E is not None, "Error: E must not be None"
    data_list = []
    for i in range(M.shape[1]):
        data_list.append((qv, M[:, i], E[:, i]))
    return np.array(data_list)

class SerialDataProxy:
    """
    SerialData class to hold data for serial processing.
    This class is used to store the data that will be processed in a serial manner.
    """
    def __init__(self, ssd, debug=False):
        if debug:
            from importlib import reload
            import molass.Backward.McVector
            reload(molass.Backward.McVector)
        from molass.Backward.McVector import compute_mc_vector_impl
        self.qvector = ssd.xr.qv
        self.intensity_array = convert_to_intensity_array(ssd.xr.qv, ssd.xr.M, ssd.xr.E)
        self.pre_recog = PreRecogProxy(ssd)
        self.mc_vector = compute_mc_vector_impl(ssd)
        self.conc_factor = ssd.get_concfactor()
        self.mapping = ssd.get_mapping()
        self.baseline_corrected = None
        self.cd_slice = None
        self.xr_j0 = ssd.xr.jv[0]
        jv = ssd.xr.jv
        self.xray_index = (jv[0] + jv[-1]) // 2

    def get_id_info(self):
        return 'SD(id=%s, corrected=%s)' % (str(id(self)), str(self.baseline_corrected))
    
    def get_cd_slice(self):
        from bisect import bisect_right
        if self.cd_slice is None:
            qmax = bisect_right(self.qvector, 0.2)   # get_setting('cd_eval_qmax')
            self.cd_slice = slice(0, qmax)
        return self.cd_slice
    
    def get_xray_scale(self):
        # return self.xray_curve.max_y
        return self.mapping.xr_curve.get_max_y()
    
    def get_xray_curve(self):
        xr_curve = self.mapping.xr_curve
        xr_curve.get_spline()   # Ensure the spline is computed. It will be used in molass_legacy.LRF.PnoScdMap
        return xr_curve