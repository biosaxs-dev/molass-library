"""
Backward.DecompResultAdapter.py

made as unified improvement from molass_legacy.Selective.V1ParamsAdapter.py
"""
import numpy as np
from molass_legacy.Models.ElutionCurveModels import EGH
from molass_legacy.Decomposer.ModelEvaluator import ModelEvaluator
from molass_legacy.Decomposer.FitRecord import FitRecord
from molass_legacy.Decomposer.UnifiedDecompResult import UnifiedDecompResult
from molass_legacy.Selective.PeakProxy import PeakProxy

def adapted_decomp_result(decomposition, ssd, mapped_curve, debug=False):
    """
    V1-compatible scheme:
    molass_legacy
        control_info = decomp_result.get_range_edit_info()
        DecompEditorFrame.make_range_info
            DecompUtils.make_range_info_impl(..., control_info, ...)

    """
    concfactor = ssd.get_concfactor()

    if debug:
        print("compute_concentration_impl: concfactor=", concfactor)

    if concfactor is None:
        from molass.Except.ExceptionTypes import NotSpecifedError
        raise NotSpecifedError("concfactor is not given as a kwarg nor acquired from a UV file.")

    xr_peaks = []
    for comp in decomposition.get_xr_components():
        xr_peaks.append(comp.ccurve.params)
    # 
    model = EGH()
    xr_curve = decomposition.xr_icurve
    uv_curve = mapped_curve
    
    fx = xr_curve.x
    y = xr_curve.y
    uv_y = uv_curve.y
    max_y = xr_curve.get_max_y()
    max_y_uv = uv_curve.get_max_y()

    opt_recs = make_xr_opt_recs_adapted(model, fx, y, xr_peaks)

    mapping = ssd.get_mapping()
    a = mapping.slope
    b = mapping.intercept
    a_ = 1/a
    b_ = -b/a
    uv_peaks = []
    for comp in decomposition.get_uv_components():
        h, m, s, t = comp.ccurve.params
        uv_peaks.append(np.array((h, m*a_+b_, s*a_, t)))

    # uv_scale = max_y_uv/max_y
    uv_scale = 1
    opt_recs_uv = make_uv_opt_recs_adapted(model, fx, uv_y, uv_peaks, uv_scale)

    if debug:
        import matplotlib.pyplot as plt
        from importlib import reload
        import molass_legacy.Decomposer.OptRecsUtils
        reload(molass_legacy.Decomposer.OptRecsUtils)
        from molass_legacy.Decomposer.OptRecsUtils import debug_plot_opt_recs_impl
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12,5))
        fig.suptitle("make_decomp_result_impl debug")
        ax1.plot(fx, uv_y, color="blue")
        debug_plot_opt_recs_impl(ax1, fx, uv_y, opt_recs_uv, color="blue")
        ax2.plot(fx, y, color="orange")
        debug_plot_opt_recs_impl(ax2, fx, y, opt_recs, color="orange")
        fig.tight_layout()
        plt.show()

    decomp_result = UnifiedDecompResult(
                xray_to_uv=None,
                x_curve=xr_curve, x=xr_curve.x, y=xr_curve.y,
                opt_recs=opt_recs,
                max_y_xray = max_y,
                model_name=model.get_name(),
                decomposer=None,
                uv_y=uv_y,
                opt_recs_uv=opt_recs_uv,
                max_y_uv = max_y_uv,
                debug_info=None,
                )

    decomp_result.set_area_proportions()
    decomp_result.remove_unwanted_elements()    # required to compute proportions used in decomp_result.identify_ignorable_elements()
    return decomp_result

def make_xr_opt_recs_adapted(model, fx, y, peaks):
    chisqr_n = np.nan
    ret_recs = []
    top_y_list = []
    for kno, params in enumerate(peaks):
        evaluator = ModelEvaluator(model, params, sign=1)
        y_ = evaluator(fx)
        m = np.argmax(y_)
        top_y = y_[m]
        top_y_list.append(top_y)
        peak = PeakProxy(top_x=fx[m], top_y=top_y)
        fit_rec = FitRecord(kno, evaluator, chisqr_n, peak)
        ret_recs.append(fit_rec)
    max_y = np.max(top_y_list)
    for kno, fit_rec in enumerate(ret_recs):
        fit_rec.peak.top_y_ratio = fit_rec.peak.top_y/max_y
    return ret_recs

def make_uv_opt_recs_adapted(model, fx, uv_y, peaks, scale):
    if model.is_traditional():
        converted_list = []
        for kno, params in enumerate(peaks):
            params_ = params.copy()
            params_[0] *= scale         # this won't work for EDM which is not traditional
            converted_list.append(params_)
    else:
        # note that non traditional models must implement this method
        converted_list = model.adjust_to_xy(peaks, fx, uv_y)

    chisqr_n = np.nan            
    ret_recs = []
    top_y_list = []
    for kno, params in enumerate(converted_list):
        evaluator = ModelEvaluator(model, params, sign=1)
        y_ = evaluator(fx)
        m = np.argmax(y_)
        top_y = y_[m]
        top_y_list.append(top_y)
        peak = PeakProxy(top_x=fx[m], top_y=top_y)
        fit_rec = FitRecord(kno, evaluator, chisqr_n, peak)
        ret_recs.append(fit_rec)
    max_y = np.max(top_y_list)
    for kno, fit_rec in enumerate(ret_recs):
        fit_rec.peak.top_y_ratio = fit_rec.peak.top_y/max_y
    return ret_recs
