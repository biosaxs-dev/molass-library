"""
    Backward.MappedCurve.py
"""

def make_mapped_curve(ssd, **kwargs):
    """make_mapped_curve(ssd, **kwargs)
    Create a mapped curve from the SecSaxsData object.
    This function estimates the mapping between the UV and XR data in the SecSaxsData object
    and generates a mapped curve accordingly.

    Parameters
    ----------
    ssd : SecSaxsData
        The SecSaxsData object containing the SAXS data.
    debug : bool, optional
        If True, enables debug mode for more verbose output.
        
    Returns
    -------
    mp_curve : Curve
        The mapped curve object.
    """
    debug = kwargs.get('debug', False)

    if ssd.uv is None:
        ssd.logger.warning("using XR data as concentration (mapped curve).")
        mp_curve = ssd.xr.get_icurve()
    else:
        mapping = ssd.estimate_mapping()
        xr_curve = ssd.xr.get_icurve()
        uv_curve = ssd.uv.get_icurve()
        mp_curve = mapping.get_mapped_curve(xr_curve, uv_curve)
        if debug:
            import matplotlib.pyplot as plt
            from molass.PlotUtils.TwinAxesUtils import align_zero_y
            fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 5))
            fig.suptitle('Mapped Curve Proof')
            ax1.plot(uv_curve.x, uv_curve.y, label='UV')
            ax2.plot(xr_curve.x, xr_curve.y, color='orange', label='XR')
            axt = ax2.twinx()
            axt.plot(mp_curve.x, mp_curve.y, label='MappedCurve')
            align_zero_y(ax1, axt)
            fig.tight_layout()
            plt.show()

    return mp_curve