"""
DenssLike.py
"""

import numpy as np
from denss.core import reconstruct_abinitio_from_scattering_profile
from learnsaxs import get_detector_info

np.int = np.int32

class DetectorInfo:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def get_detector_info_from_density(q, rho, dmax=100):
    F = np.fft.fftn(rho)
    info = get_detector_info(q, F)
    I = info.y
    sigq = I*0.03   # 3% error
    qdata, Idata, sigqdata, qbinsc, Imean, chi, rg, supportV, rho, side, fit, final_chi2 = reconstruct_abinitio_from_scattering_profile(q, I, sigq, dmax, rho_start=rho, steps=1, ne=10000)
    return DetectorInfo(q=q, y=Idata)