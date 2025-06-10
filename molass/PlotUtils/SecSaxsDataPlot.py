"""
    PlotUtils.SecSaxsDataPlot.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from molass.PlotUtils.MatrixPlot import simple_plot_3d

def plot_3d_impl(ssd, xr_only=False, uv_only=False, **kwargs):
    if xr_only or uv_only:
        ncols = 1
        figsize = (6,5)
    else:
        ncols = 2
        figsize = (12,5)
    fig, axes = plt.subplots(ncols=ncols, figsize=figsize, subplot_kw=dict(projection='3d'))

    labelkwarg = dict(fontsize=9)
    tickkwarg = dict(labelsize=9)

    if uv_only:
        ax1 = axes
        ax2 = None
    elif xr_only:
        ax1 = None
        ax2 = axes
    else:
        ax1, ax2 = axes

    if ax1 is not None:
        ax1.set_title("UV")
        uv = ssd.uv
        if uv is not None:
            ax1.set_xlabel("wavelength", **labelkwarg)
            ax1.set_ylabel("frames", **labelkwarg)
            ax1.set_zlabel("absorbance", **labelkwarg)
            simple_plot_3d(ax1, uv.M, x=uv.iv, y=uv.jv, **kwargs)
            for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
                axis.set_tick_params(**tickkwarg)

    if ax2 is not None:
        ax2.set_title("XR")
        xr = ssd.xr
        if xr is not None:
            ax2.set_xlabel("Q", **labelkwarg)
            ax2.set_ylabel("frames", **labelkwarg)
            ax2.set_zlabel("scattering", **labelkwarg)
            simple_plot_3d(ax2, xr.M, x=xr.iv, y=xr.jv, **kwargs)
            for axis in [ax2.xaxis, ax2.yaxis, ax2.zaxis]:
                axis.set_tick_params(**tickkwarg)

    fig.tight_layout()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, (ax1, ax2))

def plot_baselines_impl(ssd, **kwargs):
    fig = plt.figure(figsize=(11,8))
    gs = GridSpec(2,7)

    title = kwargs.get('title', None)
    if title is not None:
        fig.suptitle(title)

    uv_icurve = ssd.uv.get_icurve()
    uv_ibaseline = ssd.uv.get_ibaseline()

    xr_icurve = ssd.xr.get_icurve()
    xr_ibaseline = ssd.xr.get_ibaseline()

    axes = []
    for i, (name, c, b) in enumerate([("UV", uv_icurve, uv_ibaseline),
                                      ("XR", xr_icurve, xr_ibaseline)]):
        ax0 = fig.add_subplot(gs[i,0])
        ax0.set_axis_off()
        ax0.text(0.8, 0.5, name, va="center", ha="center", fontsize=20)

        ax1 = fig.add_subplot(gs[i,1:4])
        ax1.plot(c.x, c.y)
        ax1.plot(b.x, b.y)

        ax2 = fig.add_subplot(gs[i,4:7])

        axes.append((ax0, ax1, ax2))

    fig.tight_layout()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, axes)


def plot_compact_impl(ssd, **kwargs):
    from molass.PlotUtils.TrimmingPlot import ij_from_slice

    title = kwargs.pop('title', None)

    trim = ssd.make_trimming_info()
    mapping = ssd.get_mapping()
    xr_curve = mapping.xr_curve
    uv_curve = mapping.uv_curve
    x = xr_curve.x
    m = xr_curve.get_max_i()
    mp_curve = mapping.get_mapped_curve(x, uv_curve)
    mp_y = mp_curve.y / mp_curve.y[m] * xr_curve.y[m]

    fig = plt.figure(figsize=(12, 5))
    if title is not None:
        fig.suptitle(title)
    gs = GridSpec(2, 2)

    # Plot the UV and XR elution curves
    ax1 = fig.add_subplot(gs[:, 0])
    ax1.plot(x, mp_y, linestyle=":", color="C0", label="mapped UV at wavelength=280")
    ax1.plot(x, xr_curve.y, color="orange", alpha=0.5, label="XR at Q=0.02")
    i, j = ij_from_slice(trim.xr_slices[1])
    ax1.axvspan(*x[[i,j]], color='green', alpha=0.1)
    ax1.axvline(x[m], color='yellow')    
    ax1.legend()

    # Plot the UV spectral curve
    ax2 = fig.add_subplot(gs[0, 1])
    n = mapping.get_mapped_index(m, xr_curve.x, uv_curve.x)
    uv_jcurve = ssd.uv.get_jcurve(j=n)
    ax2.plot(uv_jcurve.x, uv_jcurve.y, color="C0", label="UV at j=%d" % n)
    uv_jslice = trim.uv_slices[0]
    i, j = ij_from_slice(uv_jslice)
    ax2.axvspan(*uv_jcurve.x[[i,j]], color='green', alpha=0.1)

    # Plot the XR spectral curve
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.set_yscale('log')

    xr_jcurve = ssd.xr.get_jcurve(j=m)
    ax3.plot(xr_jcurve.x, xr_jcurve.y, color="orange", alpha=0.5, label="XR at j=%d" % m)
    xr_jslice = trim.xr_slices[0]
    i, j = ij_from_slice(xr_jslice)
    ax3.axvspan(*xr_jcurve.x[[i,j]], color='green', alpha=0.1)

    fig.tight_layout()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, (ax1, ax2, ax3))