"""
LowRank.RigorousImplement
"""
import os
import numpy as np
from importlib import reload

def make_dsets_from_decomposition(decomposition, rg_curve, debug=False):
    from molass_legacy.Optimizer.OptDataSets import OptDataSets
    from molass_legacy.SecSaxs.ElCurve import ElCurve
    if debug:
        import molass.Bridge.LegacyRgCurve
        reload(molass.Bridge.LegacyRgCurve)
    from molass.Bridge.LegacyRgCurve import LegacyRgCurve
    ssd = decomposition.ssd
    xr_curve = ElCurve(*decomposition.xr_icurve.get_xy())
    D = ssd.xr.M
    E = ssd.xr.E
    uv_curve = ElCurve(*decomposition.uv_icurve.get_xy())
    U = ssd.uv.M
    dsets = ((xr_curve, D), LegacyRgCurve(xr_curve, rg_curve), (uv_curve, U))
    return OptDataSets(None, None, dsets=dsets, E=E)

def make_basecurves_from_decomposition(decomposition, debug=False):
    if debug:
        import molass.Bridge.SdProxy
        reload(molass.Bridge.SdProxy)
        import molass.Bridge.LegacyBaselines
        reload(molass.Bridge.LegacyBaselines)
    from molass.Bridge.SdProxy import SdProxy
    from molass.Bridge.LegacyBaselines import make_basecurves_from_sd
    ssd = decomposition.ssd
    sd = SdProxy(ssd)
    baseline_type = 1
    return make_basecurves_from_sd(sd, baseline_type, debug=debug)

def construct_legacy_optimizer(dsets, baseline_objects, spectral_vectors, num_components=3, model="EGH", method="BH", debug=False):
    from molass_legacy.Optimizer.OptimizerUtils import get_function_code
    from molass_legacy.Optimizer.FuncImporter import import_objective_function
    function_code = get_function_code(model)
    function_class = import_objective_function(function_code)
    optimizer = function_class(
        dsets,
        num_components + 1,
        xr_base_curve=baseline_objects[1],
        uv_base_curve=baseline_objects[0],
        qvector=spectral_vectors[0],
        wvector=spectral_vectors[1],
        )
    return optimizer

def make_rigorous_initparams_impl(decomposition, baseparams, debug=False):
    # XR initial parameters
    xr_params = []
    for ccurve in decomposition.xr_ccurves:
        xr_params.append(ccurve.get_params())
    xr_params = np.array(xr_params)
    # XR baseline parameters
    xr_baseparams = baseparams[1]

    # Rg parameters
    rg_params = decomposition.get_rgs()

    # Mapping parameters
    a, b = decomposition.ssd.get_mapping()

    # UV initial parameters
    uv_params = []
    for uv_ccurve in decomposition.uv_ccurves:
        uv_params.append(uv_ccurve.get_params()[0])

    # UV baseline parameters
    uv_baseparams = baseparams[0]

    # SecCol parameters
    x = decomposition.ssd.xr.get_icurve().x
    init_mappable_range = (x[0], x[-1])

    # SecCol parameters
    if debug:
        import molass_legacy.SecTheory.SecEstimator
        reload(molass_legacy.SecTheory.SecEstimator)
    from molass_legacy.SecTheory.SecEstimator import guess_initial_secparams
    Npc, rp, tI, t0, P, m = guess_initial_secparams(xr_params, rg_params, poresize=70)
    seccol_params = np.array([Npc, rp, tI, t0, P, m])

    return np.concatenate([xr_params.flatten(), xr_baseparams, rg_params, (a, b), uv_params, uv_baseparams, init_mappable_range, seccol_params])

def make_rigorous_decomposition_impl(decomposition, rgcurve, analysis_folder=None, niter=20, method="BH", use_legacy=True, debug=False):
    """
    Make a rigorous decomposition using a given RG curve.

    Parameters
    ----------
    decomposition : Decomposition
        The initial decomposition to refine.
    rgcurve : RgComponentCurve
        The Rg component curve to use for refinement.
    debug : bool, optional
        If True, enable debug mode with additional output.

    Returns
    -------
    Decomposition
        The refined decomposition object.
    """
    if use_legacy:
        from molass_legacy._MOLASS.SerialSettings import get_setting, set_setting
        if analysis_folder is None:
            analysis_folder = get_setting('analysis_folder')
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

    # make datasets and basecurves
    from molass_legacy.RgProcess.RgCurve import check_rg_folder
    dsets = make_dsets_from_decomposition(decomposition, rgcurve, debug=debug)
    basecurves, baseparams = make_basecurves_from_decomposition(decomposition, debug=False)
    rg_folder_ok = check_rg_folder(rg_folder)
    if not rg_folder_ok:
        rgcurve_ = dsets[1]
        rgcurve_.export(rg_folder)

    # DataTreatment
    from molass_legacy.SecSaxs.DataTreatment import DataTreatment
    trimming = 2
    correction = 1
    unified_baseline_type = 1
    treat = DataTreatment(route="v2", trimming=trimming, correction=correction, unified_baseline_type=unified_baseline_type)
    treat.save()
    decomposition.ssd.trimming.update_legacy_settings()

    # construct legacy optimizer
    spectral_vectors = decomposition.ssd.get_spectral_vectors()
    model = decomposition.xr_ccurves[0].model
    num_components = decomposition.num_components
    optimizer = construct_legacy_optimizer(dsets, basecurves, spectral_vectors, num_components=num_components, model=model, method=method, debug=debug)

    from molass_legacy.Optimizer.Scripting import set_optimizer_settings
    set_optimizer_settings(num_components=num_components, model=model, method=method)
    # make init_params
    init_params = decomposition.make_rigorous_initparams(baseparams)
    optimizer.prepare_for_optimization(init_params)
    
    # run optimization
    from molass_legacy.Optimizer.Scripting import run_optimizer
    x_shifts = dsets.get_x_shifts()
    run_optimizer(optimizer, init_params, niter=niter, x_shifts=x_shifts)

    if debug:
        import molass.Rigorous.RunInfo
        reload(molass.Rigorous.RunInfo)
    from molass.Rigorous.RunInfo import RunInfo
    return RunInfo(optimizer=optimizer, dsets=dsets, init_params=init_params)