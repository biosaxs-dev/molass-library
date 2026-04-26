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

def make_rigorous_decomposition_impl(decomposition, rgcurve, analysis_folder=None, niter=20, method="BH", frozen_components=None, trimmed_ssd=None, clear_jobs=True, function_code=None, in_process=False, monitor=True, debug=False):
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
    in_process : bool, optional
        If True, run the optimizer **in this Python process** instead of
        spawning a subprocess.  The library-prepared optimizer (with the
        live dsets, base curves, and spectral vectors built above) is the
        one that runs — no re-derivation from disk, no parent/subprocess
        divergence.  This is the recommended path for notebook use; the
        default remains ``False`` (subprocess) during the opt-in phase.
        See ``molass-library/Copilot/DESIGN_split_optimizer_architecture.md``.
    monitor : bool, optional
        Only meaningful when ``in_process=False``.  If True (default),
        spawn the subprocess via ``MplMonitor`` so the live ipywidgets
        dashboard updates as the optimizer accepts new minima.  If False,
        spawn the subprocess directly via ``BackRunner`` and block until
        it exits — no widget, no live polling.  Use ``monitor=False`` for
        batch/comparison runs where the dashboard is not needed (and to
        avoid known fragility of the matplotlib widget pipeline on
        Python 3.14 / degraded ipywidgets CDN).
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

        # Drop a breadcrumb so external observers can find this run even
        # while the kernel is busy.  See molass/Rigorous/RunRegistry.py.
        try:
            from molass.Rigorous.RunRegistry import write_run_manifest
            write_run_manifest(
                analysis_folder,
                role="analysis",
                method=method,
                niter=niter,
                in_process=in_process,
                monitor=monitor,
                analysis_folder=analysis_folder,
                status="starting",
            )
        except Exception:
            pass

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

    if in_process:
        # In-process path: skip subprocess + MplMonitor entirely.  The
        # optimizer object built above is the one that runs.  This
        # eliminates the parent/subprocess data-derivation divergence
        # diagnosed in #117 / #119 — there is no second derivation.
        # See molass-library/Copilot/DESIGN_split_optimizer_architecture.md.
        if debug:
            import molass_legacy.Optimizer.InProcessRunner
            reload(molass_legacy.Optimizer.InProcessRunner)
        from molass_legacy.Optimizer.InProcessRunner import run_optimizer_in_process

        result, work_folder = run_optimizer_in_process(
            optimizer, init_params, niter=niter, method=method,
            x_shifts=x_shifts, clear_jobs=clear_jobs, debug=debug,
        )

        # Breadcrumb: drop a manifest in the work folder too, and update
        # the analysis-folder manifest with completion + work_folder link.
        try:
            from molass.Rigorous.RunRegistry import write_run_manifest, update_run_manifest
            write_run_manifest(
                work_folder,
                role="work",
                method=method, niter=niter,
                in_process=True, monitor=False,
                analysis_folder=analysis_folder,
                status="completed",
            )
            update_run_manifest(
                analysis_folder,
                work_folder=work_folder,
                status="completed",
            )
        except Exception:
            pass

        if debug:
            import molass.Rigorous.RunInfo
            reload(molass.Rigorous.RunInfo)
        from molass.Rigorous.RunInfo import RunInfo
        run_info = RunInfo(
            ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets,
            init_params=init_params, monitor=None,
            analysis_folder=analysis_folder, decomposition=decomposition,
        )
        run_info.in_process_result = result
        run_info.work_folder = work_folder
        return run_info

    if not monitor:
        # Subprocess path WITHOUT MplMonitor.  Used by batch / comparison
        # runs (e.g. compare_optimization_paths) where the live ipywidgets
        # dashboard is not needed and would re-introduce the matplotlib /
        # widget fragility we are trying to escape with split-architecture.
        if debug:
            import molass_legacy.Optimizer.BackRunner
            reload(molass_legacy.Optimizer.BackRunner)
        from molass_legacy.Optimizer.BackRunner import BackRunner

        runner = BackRunner(xr_only=optimizer.get_xr_only(), shared_memory=False)
        # Mirror MplMonitor.run_impl: ensure optimizer is prepared before launch.
        # (already done above in `optimizer.prepare_for_optimization(init_params)`)
        runner.run(optimizer, init_params, niter=niter, x_shifts=x_shifts,
                   debug=debug)
        # Breadcrumb: now that the runner has a working_folder + subprocess
        # PID, expose them so external observers can find the live run.
        try:
            from molass.Rigorous.RunRegistry import write_run_manifest, update_run_manifest
            sub_pid = getattr(runner.process, "pid", None)
            write_run_manifest(
                runner.working_folder,
                role="work",
                method=method, niter=niter,
                in_process=False, monitor=False,
                analysis_folder=analysis_folder,
                subprocess_pid=sub_pid,
                status="running",
            )
            update_run_manifest(
                analysis_folder,
                work_folder=runner.working_folder,
                subprocess_pid=sub_pid,
                status="running",
            )
        except Exception:
            pass
        # Block until the subprocess exits.  Comparison flow will then read
        # results from disk via wait_for_rigorous_results / list_rigorous_jobs.
        rc = runner.process.wait()
        try:
            from molass.Rigorous.RunRegistry import update_run_manifest
            update_run_manifest(
                runner.working_folder,
                status="completed",
                subprocess_returncode=rc,
            )
            update_run_manifest(
                analysis_folder,
                status="completed",
                subprocess_returncode=rc,
            )
        except Exception:
            pass
        if debug:
            print(f"BackRunner subprocess exited with returncode={rc}")

        if debug:
            import molass.Rigorous.RunInfo
            reload(molass.Rigorous.RunInfo)
        from molass.Rigorous.RunInfo import RunInfo
        run_info = RunInfo(
            ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets,
            init_params=init_params, monitor=None,
            analysis_folder=analysis_folder, decomposition=decomposition,
        )
        run_info.work_folder = runner.working_folder
        run_info.subprocess_returncode = rc
        return run_info

    monitor = run_optimizer(optimizer, init_params, niter=niter, x_shifts=x_shifts, clear_jobs=clear_jobs)

    # Wire dsets to monitor so the Export Data button can work (issue #96)
    monitor.dsets = dsets

    # Display rendering uses the parent optimizer (issues #118, #128, #129).
    #
    # History:
    #   #118 originally introduced `monitor_optimizer` (a subprocess-equivalent
    #        optimizer built via `create_optimizer_from_job`) so the monitor's
    #        on-screen per-snapshot SV would match callback.txt SV.
    #   #128 changed the panel title to show `best_sv` (aggregated from
    #        callback.txt by MplMonitor) instead of the per-snapshot SV.
    #        The per-snapshot SV computed inside `plot_objective_func` is now
    #        discarded — only the plot rendering still uses `display_optimizer`.
    #   #129 the subprocess-equivalent optimizer renders curves in the
    #        original frame-number domain (its disk-loaded dsets), while the
    #        parent uses the trimmed (0..N-1) domain that the EGH parameters
    #        in `init_params` are expressed in. Mixing them shifted the UV /
    #        Rg / Xray panels off-axis. Patching `xr_curve.x` / `uv_curve.x`
    #        on the monitor optimizer is unsafe because `objective_func`
    #        reads them at every evaluation — see Fix #21 / G0346.objective_func.
    #
    # Resolution: leave `monitor_optimizer = None` so `MplMonitor` falls back
    # to the parent `optimizer` for plot rendering. The title still shows
    # `best_sv` from callback.txt (#128), so #118's user-visible guarantee
    # is preserved without the coordinate-system conflict.
    monitor.monitor_optimizer = None

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