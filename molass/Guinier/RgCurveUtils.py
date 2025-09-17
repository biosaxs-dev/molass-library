"""
    This module contains functions used to calculate a Rg curve,
    which is maked of Rg values computed from scattering curves.
"""
import os
import numpy as np
from tqdm import tqdm

ADD_ALL_RESULTS = True

def compute_rgcurve_info(xrdata):
    from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
    qv = xrdata.qv
    xrM = xrdata.M
    xrE = xrdata.E
    rginfo_list = []
    for j in tqdm(range(xrM.shape[1])):
        sg = SimpleGuinier(np.array([qv, xrM[:,j], xrE[:,j]]).T)
        if sg.Rg is not None or ADD_ALL_RESULTS:
            # rginfo_list.append((j, sg.Rg, sg.score))
            rginfo_list.append((j, sg))
    return rginfo_list

def compute_rgcurve_info_atsas(xrdata):
    from molass_legacy.ATSAS.AutorgRunner import AutorgRunner
    from molass_legacy._MOLASS.SerialSettings import set_setting

    cwd = os.getcwd()
    result_folder = os.path.join(cwd, 'atsas-result')
    os.makedirs(result_folder, exist_ok=True)
    set_setting('analysis_folder', result_folder)

    runner = AutorgRunner()
    qv = xrdata.qv
    xrM = xrdata.M
    xrE = xrdata.E
    rginfo_list = []
    for j in tqdm(range(xrM.shape[1])):
        orig_result, eval_result = runner.run_from_array(np.array([qv, xrM[:,j], xrE[:,j]]).T)
        if orig_result is not None and orig_result.Rg is not None or ADD_ALL_RESULTS:
            # rginfo_list.append((j, orig_result.Rg, orig_result.Quality))
            rginfo_list.append((j, orig_result))
    return rginfo_list