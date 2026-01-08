"""
LowRank.RigorousImplement
"""
import os
import numpy as np
from importlib import reload

def make_rigorous_decomposition_impl(decomposition, rgcurve, analysis_folder=None, niter=20, method="BH", debug=False):
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
    import molass.Rigorous.LegacyBridgeUtils
    reload(molass.Rigorous.LegacyBridgeUtils)
    from molass.Rigorous.LegacyBridgeUtils import (prepare_rigorous_folders,
                                                    make_dsets_from_decomposition,
                                                    make_basecurves_from_decomposition,
                                                    construct_legacy_optimizer
                                                    )

    dsets, basecurves, baseparams = prepare_rigorous_folders(decomposition, rgcurve, analysis_folder=analysis_folder, debug=debug)

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
    optimizer.set_xr_only(not decomposition.ssd.has_uv())

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
    return RunInfo(ssd=decomposition.ssd, optimizer=optimizer, dsets=dsets, init_params=init_params)