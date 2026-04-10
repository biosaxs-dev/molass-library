"""
Rigorous.RigorousImplement

Subprocess Coordinate Contract (Issue #80)
==========================================
When ``optimize_rigorously()`` exports data for the legacy subprocess
(``needs_export=True``, e.g. anomaly-masked datasets), the following
contract applies:

1. Exported filenames carry original frame numbers from ``ssd.xr.jv``
   (e.g. ``PREFIX_00032.dat``), so the legacy loader sets
   ``start_file_no`` correctly.
2. The restrict-lists written to ``trimming.txt`` are identity
   ``(0, N, N)`` — no re-trimming, since the data is already trimmed.
3. The subprocess does NOT need ``elution_recognition``, anomaly masks,
   or original trimming info — all preprocessing is already applied.
"""
import os
import numpy as np
from importlib import reload

def _set_identity_restrict_lists(ssd):
    """Set identity (full-range) restrict_lists for already-exported data.

    When the SSD has been exported to temp_in_folder, the subprocess loads
    the already-trimmed data.  The restrict_lists must reference the exported
    data dimensions (identity slices), not the original raw dimensions.
    """
    from molass_legacy._MOLASS.SerialSettings import set_setting
    from molass_legacy.Trimming.TrimmingInfo import TrimmingInfo as LegacyTrimmingInfo

    xr = ssd.xr
    uv = ssd.uv

    if xr is not None:
        n_frames = xr.M.shape[1]   # number of exported XR frames
        n_q = xr.M.shape[0]        # number of exported q-values
        xr_restrict = [
            LegacyTrimmingInfo(1, 0, n_frames, n_frames),
            LegacyTrimmingInfo(1, 0, n_q, n_q),
        ]
    else:
        xr_restrict = None

    if uv is not None:
        n_uv_frames = uv.M.shape[1]
        n_wl = uv.M.shape[0]
        uv_restrict = [
            LegacyTrimmingInfo(1, 0, n_uv_frames, n_uv_frames),
            LegacyTrimmingInfo(1, 0, n_wl, n_wl),
        ]
    else:
        uv_restrict = None

    set_setting('xr_restrict_list', xr_restrict)
    set_setting('uv_restrict_list', uv_restrict)

def _compute_basic_floor(decomposition, data_ssd=None):
    """Compute basic property floor values from the quick decomposition.

    These floor values set a lower bound on physical plausibility that the
    rigorous optimizer must not violate (pipeline monotonicity principle).

    Parameters
    ----------
    data_ssd : SecSaxsData, optional
        If provided, use this SSD's data matrix for P reconstruction
        (should match what the optimizer actually optimizes against).
    """
    floor = {}
    # P-matrix negativity: measure how negative the quick result's P columns are
    # (should be near zero for a good quick result)
    ssd = data_ssd if data_ssd is not None else decomposition.ssd
    xr_M = ssd.xr.M
    uv_M = ssd.uv.M if ssd.has_uv() else None

    # Reconstruct P matrices from quick result via pseudoinverse
    C_xr = np.array([c.y for c in decomposition.xr_ccurves])
    P_xr = xr_M @ np.linalg.pinv(C_xr)
    floor["p_neg_norm_xr"] = np.linalg.norm(P_xr[P_xr < 0])

    if uv_M is not None and decomposition.uv_ccurves is not None:
        C_uv = np.array([c.y for c in decomposition.uv_ccurves])
        P_uv = uv_M @ np.linalg.pinv(C_uv)
        floor["p_neg_norm_uv"] = np.linalg.norm(P_uv[P_uv < 0])

    # Note: 1D fitting floor is not yet included because the quick result's
    # normalized_rmsd values are not directly accessible here. The P-negativity
    # floor is the most critical constraint for preventing the ATP-like regression.
    return floor

def _apply_anomaly_interpolation(uncorrected_ssd, corrected_ssd=None):
    """Return a copy of *uncorrected_ssd* with anomalous frames interpolated.

    When the SSD has an anomaly mask (e.g. negative-peak region from ATP
    absorption), the excluded columns of the data matrix are replaced with
    per-row linear interpolation — the same smooth bridging that
    ``corrected_copy()`` applies after baseline subtraction.

    If no anomaly mask is present, the original SSD is returned unchanged
    (no copy is made).

    Parameters
    ----------
    uncorrected_ssd : SecSaxsData
        Trimmed but not baseline-corrected SSD to interpolate.
    corrected_ssd : SecSaxsData, optional
        Baseline-corrected SSD whose cached ``xr.anomaly_mask`` (a concrete
        boolean array set by ``corrected_copy()``) is used to determine which
        frames to exclude.  Falls back to ``uncorrected_ssd.xr`` if not given.
    """
    from molass.DataObjects.SecSaxsData import SecSaxsData

    # Prefer the corrected SSD for mask resolution: corrected_copy() caches
    # the resolved mask (concrete boolean array) from pre-correction auto-detect.
    # This avoids re-running auto-detection here.
    mask_source = corrected_ssd.xr if corrected_ssd is not None else uncorrected_ssd.xr
    exclude = SecSaxsData._resolve_neg_peak_exclude(mask_source)
    if exclude is None or not exclude.any():
        return uncorrected_ssd

    # Work on a copy so the caller's SSD is not modified
    ssd = uncorrected_ssd.copy(
        trimmed=uncorrected_ssd.trimmed,
        trimming=uncorrected_ssd.trimming,
        datafiles=getattr(uncorrected_ssd, 'datafiles', None),
    )
    SecSaxsData._interpolate_excluded(ssd.xr.M, exclude)

    # Interpolate UV frames corresponding to the XR anomaly region
    if ssd.uv is not None:
        mapping = uncorrected_ssd.get_mapping()
        if mapping is not None and not isinstance(mapping, tuple):
            xr_frames_excluded = ssd.xr.jv[exclude]
            uv_frames_mapped = mapping.slope * xr_frames_excluded + mapping.intercept
            uv_lo, uv_hi = uv_frames_mapped.min(), uv_frames_mapped.max()
            uv_exclude = (ssd.uv.jv >= uv_lo) & (ssd.uv.jv <= uv_hi)
            if uv_exclude.any():
                SecSaxsData._interpolate_excluded(ssd.uv.M, uv_exclude)

    return ssd

def make_rigorous_decomposition_impl(decomposition, rgcurve, analysis_folder=None, niter=20, method="BH", frozen_components=None, uncorrected_ssd=None, clear_jobs=True, debug=False):
    """
    Make a rigorous decomposition using a given RG curve.

    Parameters
    ----------
    decomposition : Decomposition
        The initial decomposition to refine (built on corrected data).
    rgcurve : RgComponentCurve
        The Rg component curve to use for refinement.
    frozen_components : list of int, optional
        0-based indices of protein components to freeze during optimization.
        Their EGH shape parameters, Rg, and UV scale will be held constant
        at the values from the initial decomposition.
    uncorrected_ssd : SecSaxsData, optional
        Trimmed but not baseline-corrected SSD.  When provided, the optimizer
        fits against this data (with baseline as a free parameter) instead of
        the corrected data in decomposition.ssd.
    debug : bool, optional
        If True, enable debug mode with additional output.

    Returns
    -------
    Decomposition
        The refined decomposition object.
    """
    import molass.Rigorous.LegacyBridgeUtils
    reload(molass.Rigorous.LegacyBridgeUtils)
    from molass.Rigorous.LegacyBridgeUtils import (prepare_rigorous_folders,
                                                    make_dsets_from_decomposition,
                                                    make_basecurves_from_decomposition,
                                                    construct_legacy_optimizer
                                                    )

    # If the uncorrected data has anomaly-masked frames, interpolate them
    # on a copy so the optimizer doesn't try to fit physically anomalous
    # signal.  This mirrors corrected_copy()'s _interpolate_excluded step.
    # The exclude mask is resolved from the *corrected* SSD because
    # auto-detection (recognition_curve.y < 0) only works after baseline
    # subtraction — uncorrected sums remain positive.
    if uncorrected_ssd is not None:
        uncorrected_ssd = _apply_anomaly_interpolation(uncorrected_ssd, corrected_ssd=decomposition.ssd)

    dsets, basecurves, baseparams, exported = prepare_rigorous_folders(decomposition, rgcurve, analysis_folder=analysis_folder, data_ssd=uncorrected_ssd, debug=debug)

    # Determine which SSD the optimizer actually sees (for settings, floor, etc.)
    data_ssd = uncorrected_ssd if uncorrected_ssd is not None else decomposition.ssd

    # DataTreatment
    from molass_legacy.SecSaxs.DataTreatment import DataTreatment
    trimming = 2
    correction = 1
    unified_baseline_type = 1
    treat = DataTreatment(route="v2", trimming=trimming, correction=correction, unified_baseline_type=unified_baseline_type)
    treat.save()
    if exported:
        # The exported data is already trimmed. Override the restrict_lists
        # so the subprocess sees identity slices (full range of exported data)
        # instead of slices referencing the original raw dimensions.
        _set_identity_restrict_lists(data_ssd)
    else:
        decomposition.ssd.trimming.update_legacy_settings()

    # construct legacy optimizer
    spectral_vectors = data_ssd.get_spectral_vectors()
    model = decomposition.xr_ccurves[0].model
    num_components = decomposition.num_components

    # Pipeline monotonicity: compute basic property floor from quick result
    basic_floor = _compute_basic_floor(decomposition, data_ssd=uncorrected_ssd)

    optimizer = construct_legacy_optimizer(dsets, basecurves, spectral_vectors, num_components=num_components, model=model, method=method, basic_floor=basic_floor, debug=debug)
    optimizer.set_xr_only(not data_ssd.has_uv())
    if frozen_components is not None:
        optimizer.set_frozen_components(frozen_components)

    from molass_legacy.Optimizer.Scripting import set_optimizer_settings
    set_optimizer_settings(num_components=num_components, model=model, method=method)
    # make init_params
    init_params = decomposition.make_rigorous_initparams(baseparams)
    optimizer.prepare_for_optimization(init_params)
    
    # run optimization
    from molass_legacy.Optimizer.Scripting import run_optimizer
    x_shifts = dsets.get_x_shifts()
    monitor = run_optimizer(optimizer, init_params, niter=niter, x_shifts=x_shifts, clear_jobs=clear_jobs)

    # Pass anomaly mask to monitor for consistent band display
    from molass.PlotUtils.AnomalyBands import get_anomaly_mask_from_ssd
    jv, mask = get_anomaly_mask_from_ssd(decomposition.ssd)
    if jv is not None:
        monitor.anomaly_jv = jv
        monitor.anomaly_mask = mask

    if debug:
        import molass.Rigorous.RunInfo
        reload(molass.Rigorous.RunInfo)
    from molass.Rigorous.RunInfo import RunInfo
    return RunInfo(ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets, init_params=init_params, monitor=monitor)