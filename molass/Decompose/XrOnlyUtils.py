"""
Decompose.XrOnlyUtils.py
"""

def make_dummy_uv_ccurves(ssd, xr_ccurves):
    # temporary work-around for the case without UV data
    from molass.SEC.Models.UvComponentCurve import UvComponentCurve
    mapping = ssd.get_mapping()
    uv_ccurves = [UvComponentCurve(xr_ccurve.x, mapping, xr_ccurve, 1) for xr_ccurve in xr_ccurves]
    return uv_ccurves
