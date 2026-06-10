"""
    This module contains functions used to calculate a Rg curve,
    which is maked of Rg values computed from scattering curves.
"""
import os
import inspect
import functools
import numpy as np
from tqdm.auto import tqdm

# Workaround: scipy.stats._axis_nan_policy_wrapper calls inspect.getfullargspec
# on every linregress call. In Python 3.13 this is very slow. Cache it.
_orig_getfullargspec = inspect.getfullargspec
_getfullargspec_cache = {}

@functools.wraps(_orig_getfullargspec)
def _cached_getfullargspec(func):
    if func not in _getfullargspec_cache:
        _getfullargspec_cache[func] = _orig_getfullargspec(func)
    return _getfullargspec_cache[func]

inspect.getfullargspec = _cached_getfullargspec

ADD_ALL_RESULTS = True

def compute_rg_curve_from_arrays(D, qv, E, jv=None, progress_cb=None):
    """Compute a library-quality RgCurve directly from numpy arrays.

    This is the array-level entry point that makes rg_curve computation
    independent of SSD or SD.  It uses the same SimpleGuinier pipeline as
    ``compute_rgcurve_info`` / ``XrData.compute_rgcurve``, but accepts raw
    arrays instead of an ``XrData`` object.

    This function is used by ``BackRunner.run()`` to compute and export the
    library rg_curve for LEG-GUI subprocess runs, closing the Guinier_deviation
    gap between LIB-IN and LEG-GUI without requiring the GUI to construct an SSD.

    Parameters
    ----------
    D : ndarray of shape (n_q, n_frames)
        Corrected XR intensity matrix (e.g. from ``ip_xr_D.npy``).
    qv : ndarray of shape (n_q,)
        q-values in Å⁻¹ (e.g. from ``ip_xr_qvector.npy``).
    E : ndarray of shape (n_q, n_frames)
        Intensity error matrix (e.g. from ``ip_xr_E.npy``).
    jv : ndarray of shape (n_frames,) or None
        Original frame numbers.  If None, uses ``np.arange(n_frames)``.
    progress_cb : callable or None
        Same signature as in ``compute_rgcurve_info``.

    Returns
    -------
    RgCurve
        Library ``molass.Guinier.RgCurve.RgCurve`` object.
    """
    from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
    from molass.Guinier.RgCurve import construct_rgcurve_from_list

    n_frames = D.shape[1]
    if jv is None:
        jv = np.arange(n_frames)
    rg_buffer = np.zeros(n_frames)
    rginfo_list = []
    for j in tqdm(range(n_frames)):
        sg = SimpleGuinier(np.array([qv, D[:, j], E[:, j]]).T)
        rg = sg.Rg
        if rg is not None and rg > 0:
            rg_buffer[j] = rg
        if progress_cb is not None:
            progress_cb(rg_buffer, j)
        if sg.Rg is not None or ADD_ALL_RESULTS:
            rginfo_list.append((int(jv[j]), sg))
    return construct_rgcurve_from_list(rginfo_list)


def compute_rgcurve_info(xrdata, progress_cb=None):
    """
    Computes Rg curve information from XR data.
    It uses the SimpleGuinier class to compute Rg values for each j-curve in the XR data.
    
    Parameters
    ----------
    xrdata : XrData
        The XR data from which to compute the Rg curve information.
    progress_cb : callable or None, optional
        Optional callback called after each frame with ``(rg_buffer, j)`` where
        ``rg_buffer`` is a float array of shape ``(n_frames,)`` containing the
        Rg values computed so far (0 for not-yet-computed frames) and ``j`` is
        the 0-based column index of the current frame.  The signature matches
        the legacy ``ProgressCallback`` so GUI callers can drive a progress bar
        and live Rg overlay with no additional adaptation.

    Returns
    -------
    rginfo_list : list of tuples
        A list of tuples where each tuple contains (index, SimpleGuinier result).
    """
    from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
    qv = xrdata.qv
    xrM = xrdata.M
    xrE = xrdata.E
    jv = xrdata.jv  # original frame numbers (may differ from 0..N after trimming)
    n_frames = xrM.shape[1]
    rg_buffer = np.zeros(n_frames)  # running buffer for progress_cb
    rginfo_list = []
    for j in tqdm(range(n_frames)):
        sg = SimpleGuinier(np.array([qv, xrM[:,j], xrE[:,j]]).T)
        rg = sg.Rg
        if rg is not None and rg > 0:
            rg_buffer[j] = rg
        if progress_cb is not None:
            progress_cb(rg_buffer, j)
        if sg.Rg is not None or ADD_ALL_RESULTS:
            # rginfo_list.append((j, sg.Rg, sg.score))
            rginfo_list.append((int(jv[j]), sg))
    return rginfo_list

def compute_rgcurve_info_atsas(xrdata):
    """
    Computes Rg curve information from XR data using ATSAS autorg.
    It uses the AutorgRunner class to compute Rg values for each j-curve in
    the XR data.
    
    Parameters
    ----------
    xrdata : XrData
        The XR data from which to compute the Rg curve information.
    Returns
    -------
    rginfo_list : list of tuples
        A list of tuples where each tuple contains (index, ATSAS Autorg result).
    """
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
    jv = xrdata.jv  # original frame numbers (may differ from 0..N after trimming)
    rginfo_list = []
    for j in tqdm(range(xrM.shape[1])):
        orig_result, eval_result = runner.run_from_array(np.array([qv, xrM[:,j], xrE[:,j]]).T)
        if orig_result is not None and orig_result.Rg is not None or ADD_ALL_RESULTS:
            # rginfo_list.append((j, orig_result.Rg, orig_result.Quality))
            rginfo_list.append((int(jv[j]), orig_result))
    return rginfo_list