"""
LowRank.ElementRecords.py
"""
from molass_legacy.Models.ElutionCurveModels import EGH

def make_element_records_impl(decomposition, ssd, mapped_curve, debug=False):
    """
    Returns the element records for the components.
    """
    if debug:
        from importlib import reload
        import molass.Backward.DecompResultAdapter
        reload(molass.Backward.DecompResultAdapter)
    from molass.Backward.DecompResultAdapter import adapted_decomp_result
    """
    task: refactoring with ssd and decomposition concerning mapping
    """
    concfactor = ssd.get_concfactor()

    if debug:
        print("compute_concentration_impl: concfactor=", concfactor)

    if concfactor is None:
        from molass.Except.ExceptionTypes import NotSpecifedError
        raise NotSpecifedError("concfactor is not given as a kwarg nor acquired from a UV file.")

    peaks = []
    for comp in decomposition.get_xr_components():
        peaks.append(comp.ccurve.params)
    # 
    model = EGH()
    xr_curve = decomposition.xr_icurve
    decomp_result = adapted_decomp_result(xr_curve, mapped_curve, model, peaks, debug=True)
    
    return decomp_result.opt_recs,  decomp_result.opt_recs_uv