"""
DenssLike.py
"""

import numpy as np
from denss.core import reconstruct_abinitio_from_scattering_profile
from .DetectorInfo import get_detector_info

np.int = np.int32

class DetectorInfo:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def exec_denss(ssd):
    from denss.core import reconstruct_abinitio_from_scattering_profile
    trimmed_ssd = ssd.trimmed_copy()
    corrected_ssd = trimmed_ssd.corrected_copy()
    data = corrected_ssd.get_denss_data()
    q = data.q
    I = data.I
    sigq = data.sigq
    dmax = 100
    print("q, I, sigq:", len(q), len(I), len(sigq))
    qdata, Idata, sigqdata, qbinsc, Imean, chi, rg, supportV, rho, side, fit, final_chi2 = reconstruct_abinitio_from_scattering_profile(q, I, sigq, dmax, ne=10000, extrapolate=True)

def get_detector_info_from_density(q, rho, dmax=100, use_denss=False):
    F = np.fft.fftn(rho)
    info = get_detector_info(q, F)
    if use_denss:
        # Use denss to reconstruct the scattering profile
        q = info.q
        I = info.y
        sigq = I*0.03   # 3% error
        qdata, Idata, sigqdata, qbinsc, Imean, chi, rg, supportV, rho, side, fit, final_chi2 = reconstruct_abinitio_from_scattering_profile(q, I, sigq, dmax, rho_start=rho, steps=1, ne=10000)
        ft_image = None
        return DetectorInfo(q=qdata, y=Idata), ft_image
    else:
        ft_image = np.abs(F)
        return info, ft_image