"""
    PlotUtils.SecSaxsDataPlot.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from molass.PlotUtils.MatrixPlot import simple_plot_3d

def plot_3d_impl(ssd, xr_only=False, uv_only=False, **kwargs):
    matrixplot_kwargs = {}
    title = kwargs.pop('title', None)
    with_2d_section_lines = kwargs.pop('with_2d_section_lines', False)
    if with_2d_section_lines:
        mapping = ssd.get_mapping()
        xr_curve = mapping.xr_curve
        uv_curve = mapping.uv_curve
        alpha = 0.4
    else:
        alpha = 1
    matrixplot_kwargs['cmap'] = 'coolwarm'
    matrixplot_kwargs['alpha'] = alpha
    matrixplot_kwargs['view_init'] = kwargs.get('view_init', {})
    matrixplot_kwargs['view_arrows'] = kwargs.get('view_arrows', False)
    wide_margin_layout = kwargs.get('wide_margin_layout', False)

    if xr_only or uv_only:
        ncols = 1
        figsize = (6,5)
    else:
        ncols = 2
        figsize = (12,5)
    
    if wide_margin_layout:
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(1,9)
        axs0 = fig.add_subplot(gs[0, 0])
        axs4 = fig.add_subplot(gs[0, 4])
        axs8 = fig.add_subplot(gs[0, 8])
        for ax in [axs0, axs4, axs8]:
            ax.set_axis_off()
        axes = [fig.add_subplot(gs[0,1:4], projection='3d'), fig.add_subplot(gs[0,5:8], projection='3d')]
    else:
        fig, axes = plt.subplots(ncols=ncols, figsize=figsize, subplot_kw=dict(projection='3d'))

    if title is not None:
        fig.suptitle(title)

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
            simple_plot_3d(ax1, uv.M, x=uv.iv, y=uv.jv, **matrixplot_kwargs)
            for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
                axis.set_tick_params(**tickkwarg)

        if with_2d_section_lines:   
            uv_x, uv_y = uv_curve.get_xy()
            ww = np.ones(len(uv_x)) * 280
            ax1.plot(ww, uv_x, uv_y, color='green', label="280 nm section line")

            m = xr_curve.get_max_i()
            n = mapping.get_mapped_index(m, xr_curve.x, uv_curve.x)
            uv_jcurve = ssd.uv.get_jcurve(j=n)
            ff = np.ones(len(uv_jcurve.x)) * n
            ax1.plot(uv_jcurve.x, ff, uv_jcurve.y, color="cyan", label="UV Absorbance at j=%d" % n)

            ax1.legend()

    if ax2 is not None:
        ax2.set_title("XR (X-ray)")
        xr = ssd.xr
        if xr is not None:
            ax2.set_xlabel("Q", **labelkwarg)
            ax2.set_ylabel("frames", **labelkwarg)
            ax2.set_zlabel("scattering", **labelkwarg)
            simple_plot_3d(ax2, xr.M, x=xr.iv, y=xr.jv, **matrixplot_kwargs)
            for axis in [ax2.xaxis, ax2.yaxis, ax2.zaxis]:
                axis.set_tick_params(**tickkwarg)

        if with_2d_section_lines:     
            xr_x, xr_y = xr_curve.get_xy()
            qq = np.ones(len(xr_x)) * 0.02
            ax2.plot(qq, xr_x, xr_y, color='green', label=r"0.02 $\AA^{-1}$ section line")
            xr_jcurve = ssd.xr.get_jcurve(j=m)
            ff = np.ones(len(xr_jcurve.x)) * m
            ax2.plot(xr_jcurve.x, ff, xr_jcurve.y, color="orange", alpha=0.5, label="XR Scattering at j=%d" % m)

            ax2.legend()

    fig.tight_layout()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, (ax1, ax2))

def plot_compact_impl(ssd, **kwargs):
    from molass.PlotUtils.TrimmingPlot import ij_from_slice
    from molass.PlotUtils.TwinAxesUtils import align_zero_y

    debug = kwargs.get('debug', False)

    title = kwargs.pop('title', None)
    baseline = kwargs.pop('baseline', False)
    ratio_curve = kwargs.pop('ratio_curve', False)
    moment_lines = kwargs.pop('moment_lines', False)

    trim = ssd.make_trimming()
    mapping = ssd.get_mapping()
    xr_curve = mapping.xr_curve
    uv_curve = mapping.uv_curve
    x = xr_curve.x
    mp_curve = mapping.get_mapped_curve(xr_curve, uv_curve, inverse_range=True, debug=debug)
    xr_max_x, xr_max_y = xr_curve.get_max_xy()
    
    fig = plt.figure(figsize=(12, 5))
    if title is not None:
        fig.suptitle(title)
    gs = GridSpec(2, 2)

    # Plot the UV and XR elution curves
    ax1 = fig.add_subplot(gs[:, 0])
    ax1.plot(x, xr_curve.y, color="orange", alpha=0.5, label="XR Elution at Q=0.02")
    axt = ax1.twinx()
    axt.grid(False)
    axt.plot(mp_curve.x, mp_curve.y, linestyle=":", color="C0", label="mapped UV Elution at wavelength=280")

    if baseline:
        uv_baseline = ssd.uv.get_ibaseline(debug=False)
        xr_baseline = ssd.xr.get_ibaseline(debug=False)
        mp_baseline = mapping.get_mapped_curve(xr_baseline, uv_baseline, inverse_range=True, debug=False)
        ax1.plot(xr_baseline.x, xr_baseline.y, color='red', label="XR Baseline")
        axt.plot(mp_baseline.x, mp_baseline.y, ls=':', color='red', label="UV Baseline")
        axt.legend(loc="center left")

    align_zero_y(ax1, axt)

    ymin, ymax = ax1.get_ylim()
    ax1.set_ylim(ymin, ymax * 1.2)
    i, j = ij_from_slice(trim.xr_slices[1])
    ax1.axvspan(*x[[i,j]], color='green', alpha=0.1)
    ax1.axvline(xr_max_x, color='yellow')
    ax1.set_xlabel("Frame Index for X-ray")    

    if ratio_curve:
        axt = ax1.twinx()
        axt.grid(False)
        ratio_curve = mapping.compute_ratio_curve(mp_curve=mp_curve, debug=debug)
        axt.plot(*ratio_curve.get_xy(), color="C2", alpha=0.5, label="UV/XR Ratio")
        ymin, ymax = axt.get_ylim()
        axt.set_ylim(0, ymax * 1.2)
        axt.legend(loc="center left")

    if moment_lines:
        moment = xr_curve.get_moment()
        xmin, xmax = ax1.get_xlim()
        for n in [1, 2, 3]:
            i, j = moment.get_nsigma_points(n)
            xi = xr_curve.x[i]
            xj = xr_curve.x[j]
            label= r'XR n-$\sigma$ bounds' if n == 1 else None
            labeled = False
            if xi >= xmin:
                ax1.axvline(xi, color='gray', linestyle=':', alpha=0.5, label=label)
                labeled = True
            if xj <= xmax:
                if labeled:
                    label = None
                ax1.axvline(xj, color='gray', linestyle=':', alpha=0.5, label=label)
    else:
        moment = None

    ax1.legend()

    # Plot the UV spectral curve
    ax2 = fig.add_subplot(gs[0, 1])
    m = xr_curve.get_max_i()
    n = mapping.get_mapped_index(m, xr_curve.x, uv_curve.x)
    uv_jcurve = ssd.uv.get_jcurve(j=n)
    ax2.plot(uv_jcurve.x, uv_jcurve.y, color="C0", label="UV Absorbance at j=%d" % n)
    uv_jslice = trim.uv_slices[0]
    i, j = ij_from_slice(uv_jslice)
    ax2.axvspan(*uv_jcurve.x[[i,j]], color='green', alpha=0.1)
    ax2.axvline(280, color='yellow')  # Assuming 280 nm is the wavelength of interest
    ax2.set_xlabel("Wavelength (nm)")
    ax2.legend()

    # Plot the XR spectral curve
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.set_yscale('log')

    xr_jcurve = ssd.xr.get_jcurve(j=m)
    ax3.plot(xr_jcurve.x, xr_jcurve.y, color="orange", alpha=0.5, label="XR Scattering at j=%d" % m)
    xr_jslice = trim.xr_slices[0]
    i, j = ij_from_slice(xr_jslice)
    ax3.axvspan(*xr_jcurve.x[[i,j]], color='green', alpha=0.1)
    ax3.axvline(0.02, color='yellow')  # Assuming xr_max_x is the Q value of interest
    ax3.set_xlabel(r"Q ($\AA^{-1}$)")
    ax3.legend()

    fig.tight_layout()

    if debug:
        plt.show()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, (ax1, ax2, ax3),
                      mapping=mapping, xr_curve=xr_curve, uv_curve=uv_curve, mp_curve=mp_curve,
                      moment=moment)