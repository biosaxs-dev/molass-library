"""
Rigorous.LegacyBridgeUtils.py
"""
import os
import numpy as np
from importlib import reload

def _make_elcurve(x, y):
    """Create ElCurve with 0-based ElutionCurve to avoid index/frame-number mismatch.

    The legacy ElutionCurve.get_peak_boundaries() uses peak_top_x values as
    array indices. When x contains frame numbers (e.g. 673–1212), peak_top_x
    values like 836 exceed the array length (540) and produce empty slices.
    Fix: build ElutionCurve with default 0-based x, then wrap in ElCurve.
    """
    from molass_legacy.SecSaxs.ElCurve import ElCurve
    from molass_legacy.SerialAnalyzer.ElutionCurve import ElutionCurve
    v1 = ElutionCurve(y)          # 0-based x → peak indices stay in-bounds
    return ElCurve(x, y, v1_curve=v1)

def make_dsets_from_decomposition(decomposition, rg_curve, data_ssd=None, debug=False):
    from molass_legacy.Optimizer.OptDataSets import OptDataSets
    if debug:
        import molass.Bridge.LegacyRgCurve
        reload(molass.Bridge.LegacyRgCurve)
    from molass.Bridge.LegacyRgCurve import LegacyRgCurve
    # Use data_ssd for the data matrix if provided (uncorrected data),
    # but fall back to decomposition.ssd (corrected data) if not.
    ssd = data_ssd if data_ssd is not None else decomposition.ssd
    # Use the icurve (single q-row at q≈0.02) for XR_2D_fitting,
    # consistent with quick_decomposition(). The icurve is the row of M
    # that the optimizer's elution model should fit to (M = PC).
    # The recognition curve (sum) is for anomaly detection, not for fitting.
    xr_curve = _make_elcurve(*ssd.xr.get_icurve().get_xy())
    D = ssd.xr.M
    E = ssd.xr.E
    if decomposition.uv is None:
        # temporary work-around for the case without UV data
        uv_curve = xr_curve
        U = D.copy()
    else:
        # Use the UV icurve from the same SSD as the matrix, so both
        # reflect the same data state (uncorrected + anomaly-interpolated).
        uv_curve = _make_elcurve(*ssd.uv.get_icurve().get_xy())
        U = ssd.uv.M
    dsets = ((xr_curve, D), LegacyRgCurve(xr_curve, rg_curve), (uv_curve, U))
    return OptDataSets(None, None, dsets=dsets, E=E)

def make_basecurves_from_decomposition(decomposition, data_ssd=None, debug=False):
    if debug:
        import molass.Bridge.SdProxy
        reload(molass.Bridge.SdProxy)
        import molass.Bridge.LegacyBaselines
        reload(molass.Bridge.LegacyBaselines)
    from molass.Bridge.SdProxy import SdProxy
    from molass.Bridge.LegacyBaselines import make_basecurves_from_sd
    # Use data_ssd for baseline fitting if provided (uncorrected data).
    ssd = data_ssd if data_ssd is not None else decomposition.ssd
    xr_only = not ssd.has_uv()
    sd = SdProxy(ssd)
    baseline_type = 1
    return make_basecurves_from_sd(sd, baseline_type, xr_only=xr_only, debug=debug)

def construct_legacy_optimizer(dsets, baseline_objects, spectral_vectors, num_components=3, model="EGH", method="BH", for_split_only=False, function_code=None, debug=False):
    from molass_legacy.Optimizer.OptimizerUtils import get_function_code, MODEL_NAME_DICT
    from molass_legacy.Optimizer.FuncImporter import import_objective_function
    if function_code is None:
        function_code = get_function_code(model)
    function_class = import_objective_function(function_code)
    if function_class is None:
        supported = sorted(set(MODEL_NAME_DICT.values()))
        raise NotImplementedError(
            f"Rigorous optimization does not support model={model!r} "
            f"(function_code={function_code!r}). "
            f"Supported models: {supported}"
        )
    optimizer = function_class(
        dsets,
        num_components + 1,
        xr_base_curve=baseline_objects[1],
        uv_base_curve=baseline_objects[0],
        qvector=spectral_vectors[0],
        wvector=spectral_vectors[1],
        for_split_only=for_split_only,
        )

    # backward compatibility for estimator setting
    model = model.upper()
    if model == "EGH":
        pass
    else:
        from molass_legacy.SecTheory.T0UpperBound import estimate_t0upper_bound
        class DummyEditor:
            def __init__(self, num_components):
                self.n_components = num_components + 1
                self.sd = None
                self.corrected_sd = None
                self.ecurves = None            
            def get_n_components(self):
                return self.n_components
 
        editor = DummyEditor(num_components)
        if model == "SDM":
            ecurve = dsets[0][0]
            t0upper_bound = estimate_t0upper_bound(ecurve)
            optimizer.params_type.get_estimator(editor, t0_upper_bound=t0upper_bound, debug=debug)
        elif model == "EDM":
            optimizer.params_type.get_estimator(editor, developing=True, debug=debug)
    
    return optimizer

def prepare_rigorous_folders(decomposition, rgcurve, analysis_folder=None, data_ssd=None, debug=False):
    from molass_legacy._MOLASS.SerialSettings import get_setting, set_setting
    if analysis_folder is None:
        analysis_folder = get_setting('analysis_folder')
    # Convert to absolute path BEFORE storing in settings.  If a relative path is
    # stored and the async optimizer thread later calls os.chdir(work_folder),
    # os.chdir is process-wide, so the main thread's FileHandler calls (e.g.
    # MplMonitor.monitor.log) would resolve the relative path against the new CWD
    # → doubled path like  jobs/000/temp_analysis_apo_bh/optimized/monitor.log.
    analysis_folder = os.path.abspath(analysis_folder)
    set_setting('analysis_folder', analysis_folder)
    optimizer_folder = os.path.join(analysis_folder, "optimized")
    set_setting('optimizer_folder', optimizer_folder)
    rg_folder = os.path.join(optimizer_folder, "rg-curve")

    if not os.path.exists(analysis_folder):
        os.makedirs(analysis_folder)
    if not os.path.exists(optimizer_folder):
        os.makedirs(optimizer_folder)
    if not os.path.exists(rg_folder):
        os.makedirs(rg_folder)

    temp_in_folder = os.path.abspath(os.path.join(analysis_folder, "temp_in_folder"))
    in_folder = get_setting('in_folder')
    # When negative-peak zeroing has been applied, the subprocess must see
    # the corrected (zeroed) matrices.  Force-export so it loads from
    # temp_in_folder instead of the original raw folder.
    needs_export = getattr(decomposition.ssd.xr, 'allow_negative_peaks', False)
    if in_folder is None or needs_export:
        in_folder = temp_in_folder
        set_setting('in_folder', in_folder)
        if not os.path.exists(in_folder):
            os.makedirs(in_folder)
    exported = False
    if os.path.exists(temp_in_folder):
        if in_folder == temp_in_folder:
            # Export the data SSD (uncorrected if provided, else corrected)
            export_ssd = data_ssd if data_ssd is not None else decomposition.ssd
            export_ssd.export(temp_in_folder)
            exported = True
        else:
            # Stale temp_in_folder from a previous run — remove it
            import shutil
            shutil.rmtree(temp_in_folder)

    # make datasets and basecurves
    dsets = make_dsets_from_decomposition(decomposition, rgcurve, data_ssd=data_ssd, debug=debug)
    basecurves, baseparams = make_basecurves_from_decomposition(decomposition, data_ssd=data_ssd, debug=False)
    # Always overwrite the rg-curve folder with the current LegacyRgCurve so that
    # the subprocess uses the exact same Rg data as the parent optimizer.
    # (molass-legacy#34 root cause: stale rg-curve from a previous run caused
    # different objective function values between parent and subprocess.)
    import shutil, time as _time
    if os.path.exists(rg_folder):
        shutil.rmtree(rg_folder)
    os.makedirs(rg_folder)
    rgcurve_ = dsets[1]
    rgcurve_.export(rg_folder)
    # Write a marker file so the subprocess can bypass check_rg_folder without
    # relying on SerialSettings propagation (molass-legacy#34).
    # trust.txt is the primary mechanism; trust_rg_curve_folder=True in
    # opt_settings.txt is kept as a belt-and-suspenders backup.
    with open(os.path.join(rg_folder, 'trust.txt'), 'w') as _f:
        _f.write('parent_exported')
    set_setting("trust_rg_curve_folder", True)

    # Also export to a SEPARATE parent-exclusive folder (molass-legacy#34 robust fix).
    # rg_curve_parent/ is never written by the subprocess, so it is immune to any
    # mysterious clearing of rg-curve/.  The subprocess checks for this folder first
    # when trust_rg_curve_folder=True.
    parent_rg_folder = os.path.join(optimizer_folder, "rg_curve_parent")
    if os.path.exists(parent_rg_folder):
        shutil.rmtree(parent_rg_folder)
    os.makedirs(parent_rg_folder)
    rgcurve_.export(parent_rg_folder)

    # Export parent's UV diff_spline so subprocess uses same baseline evaluation
    # (molass-legacy#34: second divergence source — UvBaseSpline.diff_spline was
    # computed from different data in subprocess vs parent).
    uv_base_curve = basecurves[0]
    _ds_exported = False
    if hasattr(uv_base_curve, 'diff_spline') and uv_base_curve.diff_spline is not None:
        if hasattr(uv_base_curve, 'curve1') and uv_base_curve.curve1 is not None:
            _ds_x = uv_base_curve.curve1.x
        else:
            # Fallback: use a range inferred from the UV data shape
            ssd_ = data_ssd if data_ssd is not None else decomposition.ssd
            _ds_x = ssd_.uv.get_icurve().x if ssd_.has_uv() else np.arange(100)
        _ds_y = uv_base_curve.diff_spline(_ds_x)
        np.save(os.path.join(optimizer_folder, 'uv_diff_spline_x.npy'), _ds_x)
        np.save(os.path.join(optimizer_folder, 'uv_diff_spline_y.npy'), _ds_y)
        _ds_exported = True

    # Diagnostic log (molass-legacy#34): confirm what the parent actually wrote.
    # Written to optimizer_folder (not rg_folder) so it survives if rg_folder is cleared.
    _prep_log = os.path.join(optimizer_folder, 'parent_prep.log')
    with open(_prep_log, 'a') as _f:
        _t = _time.strftime('%H:%M:%S')
        _f.write(f"[{_t}] prepare_rigorous_folders: export completed\n")
        _f.write(f"  rg_folder={rg_folder}\n")
        _f.write(f"  rg_folder ok.stamp: {os.path.exists(os.path.join(rg_folder, 'ok.stamp'))}\n")
        _f.write(f"  rg_folder trust.txt: {os.path.exists(os.path.join(rg_folder, 'trust.txt'))}\n")
        _f.write(f"  parent_rg_folder ok.stamp: {os.path.exists(os.path.join(parent_rg_folder, 'ok.stamp'))}\n")
        _f.write(f"  parent_rg_folder files: {sorted(os.listdir(parent_rg_folder))}\n")
        _f.write(f"  uv_diff_spline exported: {_ds_exported}\n")
        if _ds_exported:
            _f.write(f"    x range [{_ds_x[0]:.1f}, {_ds_x[-1]:.1f}] len={len(_ds_x)}\n")

    return dsets, basecurves, baseparams, exported

