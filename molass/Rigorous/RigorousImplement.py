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

def _load_best_init_params(analysis_folder, init_params):
    """Load the best params from previous jobs when resuming (``clear_jobs=False``).

    Scans ``analysis_folder/optimized/jobs/*/callback.txt``, finds the job
    with the global minimum ``fv``, and returns the corresponding best params.

    Returns ``None`` if no valid previous jobs are found (so the caller falls
    back to the original ``decomp``-derived ``init_params``).

    The length of the returned array is verified against ``init_params`` to
    guard against mismatched runs (e.g. different ``num_components``).
    """
    jobs_dir = os.path.join(analysis_folder, "optimized", "jobs")
    if not os.path.isdir(jobs_dir):
        return None

    try:
        from molass_legacy.Optimizer.StateSequence import read_callback_txt_impl
        from molass_legacy.Optimizer.Scripting import get_params
    except ImportError:
        return None

    best_fv = None
    best_job = None

    for job_name in sorted(os.listdir(jobs_dir)):
        job_dir = os.path.join(jobs_dir, job_name)
        cb_file = os.path.join(job_dir, "callback.txt")
        if not os.path.isfile(cb_file):
            continue
        try:
            fv_list, _ = read_callback_txt_impl(cb_file)
            if not fv_list:
                continue
            job_best_fv = min(entry[1] for entry in fv_list)
            if best_fv is None or job_best_fv < best_fv:
                best_fv = job_best_fv
                best_job = job_dir
        except Exception:
            continue

    if best_job is None:
        return None

    try:
        best = get_params(best_job)
        if best is not None and len(best) == len(init_params):
            print(f"Resume: loading best params from {os.path.basename(best_job)} "
                  f"(fv={best_fv:.4f}) as init_params.")
            return best
    except Exception:
        pass

    return None


def make_rigorous_decomposition_impl(decomposition, rgcurve, analysis_folder=None, niter=20, method="BH", frozen_components=None, frozen_param_groups=None, trimmed_ssd=None, clear_jobs=True, function_code=None, in_process=True, monitor=True, async_=True, progress='dashboard', max_trials=0, debug=False, _dry_run=False, ns_narrow_bounds=True, ns_adaptive_nsteps=False, ns_nsteps=None):
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
        Iteration budget.  Meaning depends on ``method``:

        * ``'BH'``: literal number of Basin-Hopping outer steps (default 20).
        * ``'NS'``: multiplied by 7 000 to form ``max_ncalls`` for UltraNest
          (``niter=20`` → 140 000 likelihood evaluations).

        Default 20.
    method : str, optional
        Optimization algorithm: ``'BH'`` (Basin-Hopping, default) or
        ``'NS'`` (Nested Sampling / UltraNest).
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
        If True (default), run the optimizer **in this Python process** instead
        of spawning a subprocess.  The library-prepared optimizer (with the
        live dsets, base curves, and spectral vectors built above) is the one
        that runs — no re-derivation from disk, no parent/subprocess divergence.
        Set ``False`` to use the legacy subprocess path (required by the tkinter
        GUI; available as an escape hatch for notebook users who need process
        isolation).
        See ``molass-library/Copilot/DESIGN_split_optimizer_architecture.md``.
    monitor : bool, optional
        Controls the ``MplMonitor`` ipywidgets dashboard.  When True
        (default), a live dashboard is shown whether the run is in-process
        or subprocess.  When False, no dashboard is created — the run
        proceeds silently.  Use ``monitor=False`` for batch / comparison
        runs (e.g. ``compare_optimization_paths``) where the widget is not
        needed.
    progress : str or None, optional
        **Deprecated and ignored** — use ``monitor=True``/``False`` instead.
        Kept in the signature only for backward compatibility.
    debug : bool, optional
        If True, enable debug mode with additional output.

    Returns
    -------
    Decomposition
        The refined decomposition object.
    """
    # NS (UltraNest) segfaults in-process (molass-library#138).
    # Auto-route to the subprocess path which has a working MplMonitor dashboard.
    _NS_METHODS = {'NS'}
    if in_process and method in _NS_METHODS:
        in_process = False

    # CMA with in_process=True, async_=True crashes the Jupyter kernel with
    # STATUS_ACCESS_VIOLATION (0xC0000005) on Windows / Python 3.14+.
    # Root cause: IPython's ProactorEventLoop (IOCP) runs concurrently with the
    # optimizer's daemon thread executing NumPy BLAS code after the cell returns.
    # Keeping the cell alive (blocking) avoids the crash → fall back to async_=False.
    # MplMonitor dashboard is not supported in the async_=False path, so monitor
    # is also forced to False to avoid a dangling watch thread.
    # See molass-library#193 and 21c_cma_inprocess_repro.ipynb for full investigation.
    _ASYNC_CRASH_METHODS = {'CMA'}
    if in_process and async_ and method in _ASYNC_CRASH_METHODS:
        import warnings as _w
        _w.warn(
            f"optimize_rigorously(in_process=True, async_=True, method={method!r}) "
            "crashes the Jupyter kernel on Windows/Python 3.14+ (STATUS_ACCESS_VIOLATION). "
            "Falling back to async_=False (blocking cell). "
            "The MplMonitor dashboard is not available in this mode. "
            "See molass-library#193.",
            UserWarning,
            stacklevel=3,
        )
        async_ = False
        monitor = False

    # progress parameter is deprecated and ignored — monitor=True/False is the
    # single control for the dashboard in both in_process paths.

    # ── Idempotency guard (molass-library#151) ──────────────────────────
    # Before doing any expensive setup, check whether a run is already live
    # for this analysis_folder / in-process thread.  If so, return the
    # existing RunInfo with a RuntimeWarning instead of starting a second run.
    import molass.Rigorous.RunInfo as _run_info_mod
    if in_process and async_:
        _existing = None
        _ref = _run_info_mod._active_inprocess
        if _ref is not None:
            _existing = _ref()   # dereference weak reference
        if _existing is not None and _existing.is_alive:
            import warnings
            warnings.warn(
                "An in-process optimization is already running "
                f"(analysis_folder={_existing.analysis_folder!r}). "
                "Returning the existing RunInfo instead of starting a new run.",
                RuntimeWarning, stacklevel=3,
            )
            return _existing
    elif not in_process and analysis_folder is not None:
        _recovered = _run_info_mod.RunInfo.reconnect(
            analysis_folder, raise_if_not_found=False
        )
        if _recovered is not None and _recovered._is_subprocess_alive():
            import warnings
            warnings.warn(
                "An optimization subprocess is already running for "
                f"analysis_folder={analysis_folder!r}. "
                "Returning the reconnected RunInfo instead of starting a new run.",
                RuntimeWarning, stacklevel=3,
            )
            return _recovered
    # ────────────────────────────────────────────────────────────────────

    # Normalize analysis_folder to an absolute path so that RunInfo,
    # _jobs_dir, write_run_manifest, and MplMonitor are all immune to
    # os.chdir() calls made by the async optimizer thread inside
    # InProcessRunner.run_optimizer_in_process().  A relative path stored
    # in SerialSettings or RunInfo.analysis_folder resolves against
    # whatever CWD is current at the time it is used — after the thread
    # calls os.chdir(work_folder) that CWD is jobs/000/, producing the
    # doubled path  ...jobs/000/<rel>/optimized/monitor.log.
    if analysis_folder is not None:
        analysis_folder = os.path.abspath(analysis_folder)

    import molass.Rigorous.LegacyBridgeUtils
    reload(molass.Rigorous.LegacyBridgeUtils)
    import molass.Rigorous.FunctionCodeUtils
    reload(molass.Rigorous.FunctionCodeUtils)
    from molass.Rigorous.LegacyBridgeUtils import (prepare_rigorous_folders,
                                                    make_dsets_from_decomposition,
                                                    make_basecurves_from_decomposition,
                                                    construct_legacy_optimizer
                                                    )

    # Warn when Pattern A is used (no trimmed_ssd, but decomposition.ssd is corrected).
    # Pattern B (trimmed_ssd=trimmed) is recommended: the optimizer fits baseline
    # as a free parameter on uncorrected data, avoiding any LPM bias baked into D.
    # Pattern A is mathematically valid at the global optimum but pre-commits to
    # the LPM baseline, which can be biased (e.g. negative on anomaly datasets).
    # See molass-library#163 (comment) and #164 for background.
    #
    # PLACEMENT CONSTRAINT: this block must remain ABOVE the `with _stack:` context
    # manager below.  The _stack enters warnings.simplefilter("ignore"), which would
    # swallow this warning silently.  Do NOT move this block inside `with _stack:`.
    if trimmed_ssd is None and getattr(decomposition.ssd, 'corrected', False):
        import warnings as _w
        _w.warn(
            "optimize_rigorously() is running on corrected data (Pattern A). "
            "The recommended approach is to pass trimmed_ssd=<your trimmed SSD> (Pattern B), "
            "which lets the optimizer fit the baseline as a free parameter on uncorrected data. "
            "This is safe to ignore, but may produce a suboptimal initial baseline "
            "if the LPM correction is biased.",
            UserWarning,
            stacklevel=3,   # chain: user cell → Decomposition.optimize_rigorously → here
        )

    # If the trimmed data has anomaly-masked frames, interpolate them
    # on a copy so the optimizer doesn't try to fit physically anomalous
    # signal.  This mirrors corrected_copy()'s _interpolate_excluded step.
    # The exclude mask is resolved from the *corrected* SSD because
    # auto-detection (recognition_curve.y < 0) only works after baseline
    # subtraction — uncorrected sums remain positive.
    if trimmed_ssd is not None:
        trimmed_ssd = _apply_anomaly_interpolation(trimmed_ssd, corrected_ssd=decomposition.ssd)

    # Dry-run mode: fire all pre-flight checks (above) and return without
    # building the optimizer.  Used by tests to verify warnings and guards
    # without running the full heavy pipeline.  (molass-library#165)
    if _dry_run:
        return None

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

    # Capture the original input data folder before prepare_rigorous_folders may
    # overwrite the global 'in_folder' setting with the temp export directory.
    from molass_legacy.SerialAnalyzer.DataUtils import get_in_folder as _get_in_folder_raw
    _original_in_folder = _get_in_folder_raw()

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
            optimizer.freeze_components(frozen_components)
        if frozen_param_groups is not None:
            optimizer.freeze_param_groups(frozen_param_groups)

        from molass_legacy.Optimizer.Scripting import set_optimizer_settings
        set_optimizer_settings(num_components=num_components, model=model, method=method,
                               ns_narrow_bounds=ns_narrow_bounds, ns_adaptive_nsteps=ns_adaptive_nsteps, ns_nsteps=ns_nsteps)
        # make init_params
        init_params = decomposition.make_rigorous_initparams(baseparams)
        # When resuming (clear_jobs=False), override with the best params found
        # across previous jobs — starting from the best known point is almost
        # always better than starting from the initial decomp params (#169).
        if not clear_jobs:
            _resume_init = _load_best_init_params(analysis_folder, init_params)
            if _resume_init is not None:
                init_params = _resume_init
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

        if debug:
            import molass.Rigorous.RunInfo
            reload(molass.Rigorous.RunInfo)
        from molass.Rigorous.RunInfo import RunInfo
        run_info = RunInfo(
            ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets,
            init_params=init_params, monitor=None,
            analysis_folder=analysis_folder, decomposition=decomposition,
            rgcurve=rgcurve,
        )

        def _run_in_process():
            # Pass a callback so run_info.work_folder is set as soon as the
            # job folder is allocated — before solve() starts.  This lets the
            # MplMonitor watch thread initialize job_state and render the upper
            # plot panel without waiting for the full run to finish. (#132)
            def _on_folder_ready(wf):
                run_info.work_folder = wf

            _result, _work_folder = run_optimizer_in_process(
                optimizer, init_params, niter=niter, method=method,
                x_shifts=x_shifts, clear_jobs=clear_jobs, debug=debug,
                work_folder_callback=_on_folder_ready,
                stop_event=run_info._stop_event,
                ns_narrow_bounds=ns_narrow_bounds,
                ns_adaptive_nsteps=ns_adaptive_nsteps,
                ns_nsteps=ns_nsteps,
            )

            # Breadcrumb: drop a manifest in the work folder too, and update
            # the analysis-folder manifest with completion + work_folder link.
            try:
                from molass.Rigorous.RunRegistry import write_run_manifest, update_run_manifest
                write_run_manifest(
                    _work_folder,
                    role="work",
                    method=method, niter=niter,
                    in_process=True, monitor=False,
                    analysis_folder=analysis_folder,
                    status="completed",
                )
                update_run_manifest(
                    analysis_folder,
                    work_folder=_work_folder,
                    status="completed",
                )
            except Exception:
                pass

            run_info.in_process_result = _result
            run_info.work_folder = _work_folder
            run_info._async_error = None
            # Clear the module-level weak reference when the run finishes.
            import molass.Rigorous.RunInfo as _run_info_mod
            _run_info_mod._active_inprocess = None

        if async_:
            import threading

            # Clear the jobs subfolder BEFORE starting the thread so that
            # _allocate_work_folder() picks jobs/000 instead of accumulating
            # jobs/001, /002, ... across repeated runs. (#132 followup)
            if clear_jobs:
                import shutil as _shutil
                _jobs_dir = os.path.join(analysis_folder, "optimized", "jobs")
                if os.path.isdir(_jobs_dir):
                    for _entry in os.listdir(_jobs_dir):
                        _ep = os.path.join(_jobs_dir, _entry)
                        if os.path.isdir(_ep):
                            _shutil.rmtree(_ep)
                os.makedirs(_jobs_dir, exist_ok=True)

            _thread = threading.Thread(target=_run_in_process, daemon=True)
            run_info._async_thread = _thread
            _thread.start()

            # Register the new run as the active in-process run.
            import molass.Rigorous.RunInfo as _run_info_mod
            import weakref
            _run_info_mod._active_inprocess = weakref.ref(run_info)

            if monitor:
                from molass_legacy.Optimizer.MplMonitor import MplMonitor
                mon = MplMonitor.for_run_info(run_info, niter=niter,
                                              max_trials=max_trials,
                                              function_code=function_code)
                mon.create_dashboard()
                mon.show()
                mon.start_watching()
                run_info.monitor = mon
                # Store original input path so draw_suptitle shows real data folder
                # (not the temp_in_folder that prepare_rigorous_folders may set)
                mon.input_folder = _original_in_folder
                # Pass anomaly mask to monitor for consistent band display
                from molass.PlotUtils.AnomalyBands import get_anomaly_mask_from_ssd
                _jv, _mask = get_anomaly_mask_from_ssd(decomposition.ssd)
                if _jv is not None:
                    mon.anomaly_jv = _jv
                    mon.anomaly_mask = _mask
        else:
            run_info._async_thread = None
            _run_in_process()

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

        # When clear_jobs=True, remove all existing job folders so BackRunner
        # starts at job 000 (BackRunner.get_work_folder() just picks the next
        # empty slot and would skip non-empty folders from a previous run).
        if clear_jobs:
            import shutil
            _jobs_dir = os.path.join(analysis_folder, "optimized", "jobs")
            if os.path.isdir(_jobs_dir):
                shutil.rmtree(_jobs_dir)

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
        # Return immediately — do NOT block on runner.process.wait().
        # load_best() polls the filesystem and returns as soon as the first
        # result lands on disk.  run_info.wait() can be used to block until
        # all iterations complete (issue #189).
        if debug:
            import molass.Rigorous.RunInfo
            reload(molass.Rigorous.RunInfo)
        from molass.Rigorous.RunInfo import RunInfo
        run_info = RunInfo(
            ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets,
            init_params=init_params, monitor=None,
            analysis_folder=analysis_folder, decomposition=decomposition,
            rgcurve=rgcurve,
        )
        run_info.work_folder = runner.working_folder
        run_info._subprocess_process = runner.process
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
    run_info = RunInfo(ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets,
                       init_params=init_params, monitor=monitor,
                       analysis_folder=analysis_folder, decomposition=decomposition,
                       rgcurve=rgcurve)
    try:
        run_info.work_folder = monitor.working_folder
    except Exception:
        pass
    return run_info