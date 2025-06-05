"""
    PlotUtils.LowRankInfoPlot.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier

def plot_components_impl(lr_info, **kwargs):
    rgcurve = kwargs.get('rgcurve', None)

    fig = plt.figure(figsize=(16, 8))
    suptitle = kwargs.get('suptitle', None)
    if suptitle is None:
        suptitle = "Component Plot"
    fig.suptitle(suptitle)

    gs = GridSpec(2,10)
    for i, name in enumerate(["UV", "XR"]):
        ax = fig.add_subplot(gs[i,0])
        ax.set_axis_off()
        ax.text(0.8, 0.5, name, va="center", ha="center", fontsize=20)

    axes = []
    for i in range(2):
        axis_row = []
        for j in range(3):
            start = 1+3*j
            ax = fig.add_subplot(gs[i,start:start+3])
            axis_row.append(ax)
        axes.append(axis_row)
    axes = np.array(axes)

    ax1 = axes[0,0]
    ax2 = axes[1,0]

    ax1.set_title("Elution Curves")

    # UV Elution Curve
    ax1.set_xlabel("Frames")
    ax1.set_ylabel("Absorbance")
    ax1.plot(*lr_info.uv_icurve.get_xy(), label="data")
    for i, c in enumerate(lr_info.uv_ccurves):
        x, y = c.get_xy()
        ax1.plot(x, y, ":", label="component-%d" % (i+1))
    ax1.legend()

    # XR Elution Curve
    ax2.set_xlabel("Frames")
    ax2.set_ylabel("Scattering Intensity")
    x, y = lr_info.xr_icurve.get_xy()
    ax2.plot(x, y, label="data")
    for i, c in enumerate(lr_info.xr_ccurves):
        cx, cy = c.get_xy()
        ax2.plot(cx, cy, ":", label="component-%d" % (i+1))
    ax2.legend()

    if rgcurve is None:
        axt = None
    else:
        axt = ax2.twinx()
        axt.set_ylabel("$R_g$")
        cm = plt.get_cmap('YlGn')
        x_ = x[rgcurve.indeces]
        axt.grid(False)
        sc = axt.scatter(x_, rgcurve.rgvalues, c=rgcurve.scores, s=3, cmap=cm)
        colorbar = kwargs.get('colorbar', False)
        if colorbar:
            fig.colorbar(sc, ax=axt, label="$R_g$ Quality", location='bottom')

    ranges = kwargs.get('ranges', None)
    if ranges is not None:
        mapping = lr_info.mapping
        uv_ylim = ax1.get_ylim()
        xr_ylim = ax2.get_ylim()
        for prange in ranges:
            color = 'powderblue' if prange.is_minor() else 'cyan'
            for (i, j) in prange:
                uv_xes = [mapping.get_mapped_x(x[k]) for k in (i, j)]
                for ax, ylim, xes in [(ax1, uv_ylim, uv_xes), (ax2, xr_ylim, x[[i,j]])]:
                    ymin, ymax = ylim
                    p = Rectangle(
                        (xes[0], ymin),     # (x,y)
                        xes[1] - xes[0],    # width
                        ymax - ymin,        # height
                        facecolor = color,
                        alpha = 0.2,
                        )
                    ax.add_patch(p)              

    ax3 = axes[0,1]
    ax4 = axes[1,1]
    ax4.set_yscale('log')
    ax3.set_title("Spectral Curves")

    ax3.set_xlabel("Wavelength [nm]")
    ax3.set_ylabel("Absorbance")

    # UV Absorbance Curves
    wv = lr_info.wv
    M, C, P = lr_info.uv_matrices[0:3]
    for i, pv in enumerate(P.T):
        ax3.plot(wv, pv, ":", color='C%d'%(i+1), label="component-%d" % (i+1))
    ax3.legend()

    # XR Scattering Curves
    ax4.set_xlabel(r"Q $[\AA^{-1}]$")
    ax4.set_ylabel(r"$\log_{10}(I)$")

    qv = lr_info.qv
    M, C, P = lr_info.xr_matrices[0:3]
    for i, pv in enumerate(P.T):
        ax4.plot(qv, pv, ":", color='C%d'%(i+1), label="component-%d" % (i+1))
    ax4.legend()

    # Guinier Plot
    ax5 = axes[0,2]
    ax6 = axes[1,2]
    ax5.set_title("XR Guinier/Kratky Plots")
    ax5.set_xlabel(r"$Q^2$")
    ax5.set_ylabel(r"$\log(I) - I_0$")

    # Kratky Plot
    ax6.set_xlabel("$QR_g$")
    ax6.set_ylabel(r"$(QR_g)^2 \times I(Q)/I_0$")

    for i, xr_component in enumerate(lr_info.get_xr_components()):
        data = xr_component.get_jcurve_array()
        pv = data[:,1]
        sg = SimpleGuinier(data)
        start = sg.guinier_start
        stop = sg.guinier_stop
        for j, slice_ in enumerate([slice(0, int(stop*1.2)), slice(start, stop)]):
            qv2 = qv[slice_]**2
            logy = np.log(pv[slice_])
            color = 'gray' if j == 0 else 'C%d'%(i+1)
            alpha = 0.5 if j == 0 else 1
            label = None if j == 0 else r"component-%d, $R_g=%.3g$" % (i+1, sg.Rg)
            ax5.plot(qv2, logy - sg.Iz, ":", color=color, alpha=alpha, label=label)
        
        qrg = qv*sg.Rg
        ax6.plot(qrg, qrg**2*pv/sg.Iz, ":", color='C%d'%(i+1), label="component-%d" % (i+1))

    ax5.legend()

    px = np.sqrt(3)
    py = 3/np.e
    ax6.axvline(px, ls=":", color="gray")
    ax6.axhline(py, ls=":", color="gray")
    ax6.axhline(0, color="red", alpha=0.5)

    xmin, xmax = ax6.get_xlim()
    ymin, ymax = ax6.get_ylim()
    dy = (ymax - ymin)*0.01
    ax6.text(px, ymin+dy, r"$ \sqrt{3} $", ha="right")
    ax6.text(xmax, py+2*dy, r"$ 3/e $", ha="right")

    ax6.legend()

    fig.tight_layout()
    fig.subplots_adjust(wspace=1.5)

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, (ax1, ax2, axt))