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

# ---------------------------------------------------------------------------
# Segment-analysis utilities
# (migrated from molass_legacy/GuinierTools/RgCurveUtils.py)
# ---------------------------------------------------------------------------
from collections import namedtuple

# Two boolean masks over the rg_curve domain:
#   all_frames: mask over the full frame range of rg_curve.x
#   segment:    mask over concatenated active segments only (shorter)
ValidBools = namedtuple('ValidBools', ['all_frames', 'segment'])

VALID_QUIALTY_LIMIT = 0.01
VALID_BASE_QUALITY = 0.3


def convert_to_milder_qualities(qualities):
    """Raise the quality floor so that low-quality frames still get some weight.

    Maps raw qualities (0–1) to a compressed range (VALID_BASE_QUALITY–1):
        out[i] = 0.3 + 0.7 * qualities[i]   for qualities[i] > 0.01

    .. deprecated::
        No longer used for Guinier_deviation weights (see molass-legacy issue #11).
        Raw qualities are now used directly in ``GuinierDeviation``.
        Kept for backward compatibility (e.g. ``max_mask`` threshold).
    """
    ret_qualities = qualities.copy()
    valid = qualities > VALID_QUIALTY_LIMIT
    ret_qualities[valid] = VALID_BASE_QUALITY + (1 - VALID_BASE_QUALITY) * qualities[valid]
    return ret_qualities


def get_connected_curve_info(rg_curve, debug=False):
    """Extract concatenated x, y, Rg, and quality arrays from a segmented Rg curve.

    Works with any object that exposes the segmented Rg interface:
    ``get_curve_segments()``, ``.qualities``, ``.states``, ``.slices``, ``.x``.
    This covers ``RgProcess.RgCurve``, ``RgProcess.RgCurveProxy``, and
    ``Bridge.LegacyRgCurve``.

    Returns
    -------
    x_ : ndarray
        Concatenated frame positions of all active segments.
    y_ : ndarray
        Corresponding elution intensities.
    rgv : ndarray
        Corresponding smoothed Rg values.
    qualities : ndarray
        Concatenated raw Guinier quality scores (one per active frame).
    valid_bools : ValidBools
        Named-tuple with two boolean masks:
        ``all_frames`` (len = len(rg_curve.x)) and
        ``segment``    (len = len(qualities)).
    """
    segments = rg_curve.get_curve_segments()
    qualities = np.concatenate(rg_curve.qualities)

    x_list = []
    y_list = []
    rg_list = []
    valid_bool_all = np.zeros(len(rg_curve.x), dtype=bool)
    valid_bool_seg_list = []
    k = 0
    for state, slice_ in zip(rg_curve.states, rg_curve.slices):
        if state == 0:
            continue
        x_, y_, rg_ = segments[k]
        x_list.append(x_)
        y_list.append(y_)
        rg_list.append(rg_)
        bvec = rg_curve.qualities[k] > VALID_QUIALTY_LIMIT
        valid_bool_all[slice_] = bvec
        valid_bool_seg_list.append(bvec)
        k += 1

    x_ = np.concatenate(x_list)
    y_ = np.concatenate(y_list)
    rgv = np.concatenate(rg_list)
    valid_bool_seg = np.concatenate(valid_bool_seg_list)

    if debug:
        import matplotlib.pyplot as mpl_plt
        fig, ax = mpl_plt.subplots()
        ax.set_title("get_connected_curve_info: debug")
        axt = ax.twinx()
        axt.grid(False)
        for dx, dy, drg in zip(x_list, y_list, rg_list):
            ax.plot(dx, dy)
            axt.plot(dx, drg, color='gray')
        axt.plot(x_, qualities * 100, color='green', alpha=0.5)
        fig.tight_layout()
        mpl_plt.show()

    return x_, y_, rgv, qualities, ValidBools(valid_bool_all, valid_bool_seg)


def get_reconstructed_curve(size, valid_bools, Cxr, rg_params):
    """Reconstruct the weighted-average Rg curve from component elution curves.

    Parameters
    ----------
    size : int
        Length of the output array (number of active frames in the segment).
    valid_bools : ValidBools
    Cxr : ndarray, shape (n_components, n_all_frames)
    rg_params : sequence of float

    Returns
    -------
    rrgv : ndarray, shape (size,)
    """
    from molass_legacy.Optimizer.NumericalUtils import safe_ratios
    ty_ = np.sum(Cxr, axis=0)[valid_bools.all_frames]
    ones = np.ones(size)
    rrgv = np.zeros(size)
    for cy, rg in zip(Cxr[:-1], rg_params):
        rrgv += safe_ratios(ones, cy[valid_bools.all_frames], ty_, debug=False) * rg
    return rrgv


def compute_rg_curves(x, xr_weights, rg_params, xr_cy_list, xr_ty, rg_curve, debug=False):
    """Compute observed and reconstructed Rg curves for each active segment.

    Returns
    -------
    rg_curves1 : list of (x, rg) tuples — observed Rg from rg_curve.segments
    rg_curves2 : list of (x, rg) tuples — model-reconstructed Rg
    """
    from molass_legacy.Optimizer.NumericalUtils import safe_ratios

    t_rg_ = np.zeros(len(x))
    ones = np.ones(len(t_rg_))
    for w, r, xr_cy in zip(xr_weights, rg_params, xr_cy_list):
        if w > 0.001:
            t_rg_ += r * safe_ratios(ones, xr_cy, xr_ty, debug=False)

    rg_curves1 = []
    rg_curves2 = []
    segments = rg_curve.segments
    k = 0
    for state, slice_ in zip(rg_curve.states, rg_curve.slices):
        if state == 0:
            continue
        x_, y_, rg_ = segments[k]
        rg_curves1.append((x_, rg_))
        rg_curves2.append((x[slice_], t_rg_[slice_]))
        k += 1

    if debug:
        import matplotlib.pyplot as mpl_plt
        fig, ax = mpl_plt.subplots()
        fig.suptitle("compute_rg_curves debug")
        axt = ax.twinx()
        axt.grid(False)
        for cy in xr_cy_list:
            ax.plot(x, cy, ":")
        ax.plot(x, xr_ty, ":", color="red")
        for (x1_, rg1_), (x2_, rg2_) in zip(rg_curves1, rg_curves2):
            axt.plot(x1_, rg1_)
            axt.plot(x2_, rg2_, ":")
        fig.tight_layout()
        mpl_plt.show()

    return rg_curves1, rg_curves2


def plot_rg_curves(ax, xrh_params, rg_params, x, xr_cy_list, xr_ty, rg_curve):
    """Plot observed and reconstructed Rg curves on *ax* (a matplotlib Axes).

    Used by the legacy model-parameter plot utilities (EghPlotUtils, etc.).
    """
    if len(xr_cy_list) > len(rg_params):
        xr_ty_ = xr_ty - xr_cy_list[-1]
    else:
        xr_ty_ = xr_ty
    weights = xrh_params / np.max(xrh_params)
    num_components = len(xrh_params)
    assert len(rg_params) == num_components

    rg_curves1, rg_curves2 = compute_rg_curves(
        x, weights, rg_params, xr_cy_list[:num_components], xr_ty_, rg_curve
    )

    k = 0
    for (x1, rg1), (x2, rg2) in zip(rg_curves1, rg_curves2):
        label = 'observed rg' if k == 0 else None
        ax.plot(x1, rg1, color='gray', alpha=0.5, label=label)
        label = 'reconstructed rg' if k == 0 else None
        ax.plot(x2, rg2, ':', color='black', label=label)
        k += 1

    ymin, ymax = ax.get_ylim()
    ax.set_ylim(min(10, ymin), max(50, ymax))
    ax.legend(loc='upper left')


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