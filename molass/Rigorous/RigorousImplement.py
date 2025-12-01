"""
LowRank.RigorousImplement
"""
import numpy as np
from importlib import reload

class DummyBasecurve:
    def __init__(self, x):
        self.x = x
        self.y = np.zeros(len(x))

    def __call__(self, x, params, y_, cy_list):
        return self.y

def make_dsets_from_decomposition(decomposition, rg_curve, debug=False):
    from molass_legacy.Optimizer.OptDataSets import OptDataSets
    ssd = decomposition.ssd
    xr_curve = decomposition.xr_icurve
    D = ssd.xr.M
    E = ssd.xr.E
    uv_curve = decomposition.uv_icurve
    U = ssd.uv.M
    dsets = ((xr_curve, D), rg_curve, (uv_curve, U))
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

def construct_legacy_optimizer(dsets, base_curves, spectral_vectors, num_components=3, model="EGH", method="BH", debug=False):
    from molass_legacy.Optimizer.OptimizerUtils import get_function_code
    from molass_legacy.Optimizer.FuncImporter import import_objective_function
    function_code = get_function_code(model)
    function_class = import_objective_function(function_code)
    optimizer = function_class(
        dsets,
        num_components + 1,
        xr_base_curve=base_curves[0],
        uv_base_curve=base_curves[1],
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
    for uv_ccurve, xr_ccurve in zip(decomposition.uv_ccurves, decomposition.xr_ccurves):
        uv_params.append(uv_ccurve.get_params()[0]/xr_ccurve.get_params()[0])

    # UV baseline parameters
    uv_baseparams = baseparams[0]

    # SecCol parameters
    x = decomposition.ssd.xr.get_icurve().x
    init_mappable_range = (x[0], x[-1])

    # SecCol parameters
    from molass_legacy.SecTheory.SecEstimator import guess_initial_secparams
    Npc, rp, tI, t0, P, m = guess_initial_secparams(xr_params, rg_params)
    seccol_params = np.array([Npc, rp, tI, t0, P, m])

    return np.concatenate([xr_params.flatten(), xr_baseparams, rg_params, uv_params, uv_baseparams, init_mappable_range, seccol_params])

def make_rigorous_decomposition_impl(decomposition, rgcurve, method="BH", debug=False):
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
    dsets = make_dsets_from_decomposition(decomposition, rgcurve, debug=debug)
    base_curves = make_base_curves_from_decomposition(decomposition, debug=debug)

    # construct legacy optimizer
    spectral_vectors = decomposition.ssd.get_spectral_vectors()
    model = decomposition.xr_ccurves[0].model
    optimizer = construct_legacy_optimizer(dsets, base_curves, spectral_vectors, num_components=decomposition.num_components, model=model, method=method, debug=debug)

    from molass_legacy.Optimizer.Scripting import set_optimizer_settings
    set_optimizer_settings(num_components=decomposition.num_components, model=model, method=method)

    # make init_params
    init_params = decomposition.make_rigorous_initparams(base_curves)
    optimizer.prepare_for_optimization(init_params)
    
    # run optimization
    from molass_legacy.Optimizer.Scripting import run_optimizer
    run_optimizer(optimizer, init_params)

    if debug:
        import molass.LowRank.Decomposition
        reload(molass.LowRank.Decomposition)
    from molass.LowRank.Decomposition import Decomposition

    ssd = decomposition.ssd
    xr_icurve = decomposition.xr_icurve
    uv_icurve = decomposition.uv_icurve
    xr_ccurves = decomposition.xr_ccurves
    uv_ccurves = decomposition.uv_ccurves

    return Decomposition(ssd, xr_icurve, xr_ccurves, uv_icurve, uv_ccurves)