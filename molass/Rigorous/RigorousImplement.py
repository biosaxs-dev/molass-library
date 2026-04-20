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

def make_rigorous_decomposition_impl(decomposition, rgcurve, analysis_folder=None, niter=20, method="BH", frozen_components=None, trimmed_ssd=None, clear_jobs=True, function_code=None, debug=False):
    """
    Make a rigorous decomposition using a given RG curve.

    Parameters
    ----------
    decomposition : Decomposition
        The initial decomposition to refine (built on corrected data).
    rgcurve : RgComponentCurve
        The Rg component curve to use for refinement.
    analysis_folder : str, optional
        The folder to save analysis results.
    niter : int, optional
        Number of iterations. Default 20.
    method : str, optional
        Optimization algorithm: ``'BH'`` (Basin-Hopping, default),
        ``'NS'`` (Nested Sampling / UltraNest), ``'MCMC'`` (emcee),
        ``'SMC'`` (Sequential Monte Carlo).
    frozen_components : list of int, optional
        0-based indices of protein components to freeze during optimization.
        Their EGH shape parameters, Rg, and UV scale will be held constant
        at the values from the initial decomposition.
    trimmed_ssd : SecSaxsData, optional
        Trimmed but not baseline-corrected SSD.  When provided, the optimizer
        fits against this data (with baseline as a free parameter) instead of
        the corrected data in decomposition.ssd.
    clear_jobs : bool, optional
        If True (default), clear existing job folders before starting.
    debug : bool, optional
        If True, enable debug mode with additional output.

    Returns
    -------
    Decomposition
        The refined decomposition object.
    """
    import molass.Rigorous.LegacyBridgeUtils
    reload(molass.Rigorous.LegacyBridgeUtils)
    import molass.Rigorous.FunctionCodeUtils
    reload(molass.Rigorous.FunctionCodeUtils)
    from molass.Rigorous.LegacyBridgeUtils import (prepare_rigorous_folders,
                                                    make_dsets_from_decomposition,
                                                    make_basecurves_from_decomposition,
                                                    construct_legacy_optimizer
                                                    )

    # If the trimmed data has anomaly-masked frames, interpolate them
    # on a copy so the optimizer doesn't try to fit physically anomalous
    # signal.  This mirrors corrected_copy()'s _interpolate_excluded step.
    # The exclude mask is resolved from the *corrected* SSD because
    # auto-detection (recognition_curve.y < 0) only works after baseline
    # subtraction — uncorrected sums remain positive.
    if trimmed_ssd is not None:
        trimmed_ssd = _apply_anomaly_interpolation(trimmed_ssd, corrected_ssd=decomposition.ssd)

    # Suppress verbose legacy output unless debug=True.
    # The pre-optimization pipeline (folder setup, dataset construction,
    # baseline fitting, optimizer construction, parameter preparation)
    # produces many diagnostic prints from molass-legacy internals that
    # are not actionable for the caller.
    # Note: always suppresses (not gated by quiet option) because the noise
    # from the rigorous pipeline is never useful in normal operation.
    import io, warnings as _warnings
    from contextlib import redirect_stdout, redirect_stderr, ExitStack

    _stack = ExitStack()
    if not debug:
        _stack.enter_context(redirect_stdout(io.StringIO()))
        _stack.enter_context(redirect_stderr(io.StringIO()))
        _wctx = _warnings.catch_warnings()
        _stack.enter_context(_wctx)
        _warnings.simplefilter("ignore")

    with _stack:
        dsets, basecurves, baseparams, exported = prepare_rigorous_folders(decomposition, rgcurve, analysis_folder=analysis_folder, data_ssd=trimmed_ssd, debug=debug)

        # Determine which SSD the optimizer actually sees (for settings, floor, etc.)
        data_ssd = trimmed_ssd if trimmed_ssd is not None else decomposition.ssd

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

        # Auto-select G1200 (SDM-Gamma) when the decomposition uses a
        # Gamma-distributed SdmColumn (k != 1.0).  See issue #89.
        if function_code is None:
            from .FunctionCodeUtils import detect_function_code
            function_code = detect_function_code(decomposition)

        optimizer = construct_legacy_optimizer(dsets, basecurves, spectral_vectors, num_components=num_components, model=model, method=method, function_code=function_code, debug=debug)
        optimizer.set_xr_only(not data_ssd.has_uv())
        if frozen_components is not None:
            optimizer.set_frozen_components(frozen_components)

        from molass_legacy.Optimizer.Scripting import set_optimizer_settings
        set_optimizer_settings(num_components=num_components, model=model, method=method)
        # make init_params
        init_params = decomposition.make_rigorous_initparams(baseparams)
        optimizer.prepare_for_optimization(init_params)

    # run optimization (outside _quiet — subprocess launch message is useful)
    from molass_legacy.Optimizer.Scripting import run_optimizer
    x_shifts = dsets.get_x_shifts()
    monitor = run_optimizer(optimizer, init_params, niter=niter, x_shifts=x_shifts, clear_jobs=clear_jobs)

    # Wire dsets to monitor so the Export Data button can work (issue #96)
    monitor.dsets = dsets

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
    return RunInfo(ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets,
                   init_params=init_params, monitor=monitor,
                   analysis_folder=analysis_folder, decomposition=decomposition)