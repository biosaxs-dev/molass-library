"""
DenssTools.py
"""

import os
import numpy as np
from molass.PackageUtils.NumbaUtils import get_ready_for_numba
get_ready_for_numba()
from molass_legacy.DENSS.denss.core import reconstruct_abinitio_from_scattering_profile
from .DetectorInfo import get_detector_info

np.int = np.int32

class DetectorInfo:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def run_denss(jcurve_array, output_folder=None, file_prefix="denss_result", debug=False):
    """run_denss(jcurve_array, output_folder=None, file_prefix="denss_result")
    Runs the DENSS algorithm on the provided j-curve data.

    Parameters
    ----------
    jcurve_array : np.ndarray
        A 2D array where each row contains q, I, and sigq values.
        The first column is q, the second is I, and the third is sigq.

    output_folder : str, optional
        The folder where the output files will be saved. If None, no files will be saved.

    file_prefix : str, optional
        A prefix for the output files. Default is "denss_result".
        A name for the data, used in the output. Default is "denss_result".

    Returns
    -------
    None
    """
    # from denss.core import reconstruct_abinitio_from_scattering_profile
    from molass_legacy.DENSS.DenssUtils import fit_data_impl, run_denss_impl
    q = jcurve_array[:,0]
    I = jcurve_array[:,1]
    sigq = jcurve_array[:,2]
    sasrec, work_info = fit_data_impl(q, I, sigq, gui=True, use_memory_data=True)
    dmax = round(sasrec.D, 2)
    if debug:
        print("dmax:", dmax)
        print("q, I, sigq:", len(q), len(I), len(sigq))
    qc = sasrec.qc
    ac = sasrec.Ic
    ec = sasrec.Icerr
    if debug:
        print("qc, ac, ec:", len(qc), len(ac), len(ec))
    
    cwd = None
    if output_folder is not None:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        cwd = os.getcwd()
        os.chdir(output_folder)
    run_denss_impl(qc, ac, ec, dmax, file_prefix, use_gpu=False)
    if cwd is not None:
        os.chdir(cwd)

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