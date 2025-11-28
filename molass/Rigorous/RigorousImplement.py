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

def make_base_curves_from_decomposition(decomposition, debug=False):
    from molass_legacy.Baseline.LinearBaseline import LinearBaseline
    ssd = decomposition.ssd
    x, y = decomposition.xr_icurve.get_xy()
    xr_baseline = DummyBasecurve(x)
    uv_baseline = DummyBasecurve(x)
    return (xr_baseline, uv_baseline)

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