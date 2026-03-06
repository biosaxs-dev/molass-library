"""
Rigorous.LegacyBridgeUtils.py
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
    if decomposition.uv is None:
        # temporary work-around for the case without UV data
        uv_curve = xr_curve
        U = D.copy()
    else:
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
    xr_only = not ssd.has_uv()
    sd = SdProxy(ssd)
    baseline_type = 1
    return make_basecurves_from_sd(sd, baseline_type, xr_only=xr_only, debug=debug)

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

def prepare_rigorous_folders(decomposition, rgcurve, analysis_folder=None, debug=False):
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

    temp_in_folder = os.path.abspath(os.path.join(analysis_folder, "temp_in_folder"))
    in_folder = get_setting('in_folder')
    if in_folder is None:
        in_folder = temp_in_folder
        print(f"Exporting SecSaxsData to temporary folder: {in_folder}")
        set_setting('in_folder', in_folder)
        if not os.path.exists(in_folder):
            os.makedirs(in_folder)
    if os.path.exists(temp_in_folder):
        assert in_folder == temp_in_folder
        decomposition.ssd.export(temp_in_folder)

    # make datasets and basecurves
    from molass_legacy.RgProcess.RgCurve import check_rg_folder
    dsets = make_dsets_from_decomposition(decomposition, rgcurve, debug=debug)
    basecurves, baseparams = make_basecurves_from_decomposition(decomposition, debug=False)
    rg_folder_ok = check_rg_folder(rg_folder)
    if not rg_folder_ok:
        rgcurve_ = dsets[1]
        rgcurve_.export(rg_folder)

    return dsets, basecurves, baseparams

