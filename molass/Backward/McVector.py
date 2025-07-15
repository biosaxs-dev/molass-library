"""
    Backward.McVector.py
"""

def compute_mc_vector_impl(ssd, **kwargs):
    debug = kwargs.get('debug', False)

    concfactor = kwargs.get('concfactor', None)
    if concfactor is None:
        concfactor = ssd.get_concfactor()

    if debug:
        print("compute_concentration_impl: concfactor=", concfactor)

    if concfactor is None:
        from molass.Except.ExceptionTypes import NotSpecifedError
        raise NotSpecifedError("concfactor is not given as a kwarg nor acquired from a UV file.")

    if ssd.uv is None:
        ssd.logger.warning("using XR data as concentration.")
        conc_curve = ssd.xr.get_icurve()
    else:
        mapping = ssd.estimate_mapping()
        xr_curve = ssd.xr.get_icurve()
        uv_curve = ssd.uv.get_icurve()
        conc_curve = mapping.get_mapped_curve(xr_curve, uv_curve)
        if debug:
            import matplotlib.pyplot as plt
            from molass.PlotUtils.TwinAxesUtils import align_zero_y
            fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
            ax1.plot(uv_curve.x, uv_curve.y, label='UV')
            ax2.plot(xr_curve.x, xr_curve.y, color='orange', label='XR')
            axt = ax2.twinx()
            axt.plot(conc_curve.x, conc_curve.y, label='McVector')
            align_zero_y(ax1, axt)
            fig.tight_layout()
            plt.show()

    return conc_curve*concfactor