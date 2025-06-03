"""
DenssTools.py
"""

import numpy as np
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from denss.core import reconstruct_abinitio_from_scattering_profile
from .DetectorInfo import get_detector_info

np.int = np.int32

class DetectorInfo:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def exec_denss(jcurve_data, data_name="data_name"):
    # from denss.core import reconstruct_abinitio_from_scattering_profile
    from molass_legacy.DENSS.DenssUtils import fit_data_impl, run_denss_impl
    q = jcurve_data.q
    I = jcurve_data.I
    sigq = jcurve_data.sigq
    sasrec, work_info = fit_data_impl(q, I, sigq, gui=True, use_memory_data=True)
    dmax = round(sasrec.D, 2)
    print("q, I, sigq:", len(q), len(I), len(sigq))
    qc = sasrec.qc
    ac = sasrec.Ic
    ec = sasrec.Icerr
    print("qc, ac, ec:", len(qc), len(ac), len(ec))
    run_denss_impl(qc, ac, ec, dmax, data_name, use_gpu=False)

def get_detector_info_from_density(q, rho, dmax=100, use_denss=False, debug=False):
    if debug:
        print("dmax=", dmax)
    F = np.fft.fftn(rho)
    if use_denss:
        # Use denss to reconstruct the scattering profile
        q = info.q
        I = info.y
        sigq = I*0.03   # 3% error
        qdata, Idata, sigqdata, qbinsc, Imean, chi, rg, supportV, rho, side, fit, final_chi2 = reconstruct_abinitio_from_scattering_profile(q, I, sigq, dmax, rho_start=rho, steps=1, ne=10000)
        ft_image = None
        return DetectorInfo(q=qdata, y=Idata), ft_image
    else:
        info = get_detector_info(q, F, dmax=dmax)
        ft_image = np.abs(F)
        return info, ft_image