"""
    PlotUtils.DecompositionPlot.py
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier

ALLOWED_KEYS = {
    'pairedranges', 'rgcurve', 'title', 'colorbar', 'debug',
}

def create_axes(fig, row_titles=["UV", "XR"]):
    gs = GridSpec(2,10)
    for i, name in enumerate(row_titles):
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
    return np.array(axes)


def plot_elution_curve(ax, icurve, ccurves, title=None, ylabel=None, **kwargs):
    if title is not None:
        ax.set_title(title)
    ax.set_xlabel("Frames")
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    x, y = icurve.get_xy()
    ax.plot(x, y, color='gray', alpha=0.5, label="data")
    proportions = kwargs.get('proportions', None)
    cy_list = []
    for i, c in enumerate(ccurves):
        cx, cy = c.get_xy()
        p = "" if proportions is None else " (%.3g)" % proportions[i]
        ax.plot(cx, cy, ":", label="component-%d" % (i+1) + p)
        cy_list.append(cy)
    ty = np.sum(cy_list, axis=0)
    ax.plot(x, ty, color='red', alpha=0.3, label="component total")
    ax.legend()

    rgcurve = kwargs.get('rgcurve', None)
    colorbar = kwargs.get('colorbar', False)
    if rgcurve is None:
        axt = None
    else:
        axt = ax.twinx()
        axt.set_ylabel("$R_g$")
        cm = plt.get_cmap('YlGn')
        x_ = x[rgcurve.indeces]
        axt.grid(False)
        sc = axt.scatter(x_, rgcurve.rgvalues, c=rgcurve.scores, s=3, cmap=cm)
        
        if colorbar:
            ax.fig.colorbar(sc, ax=axt, label="$R_g$ Quality", location='bottom')
        ymin, ymax = axt.get_ylim()
        axt.set_ylim(min(0,ymin), ymax*1.5)
    return axt

def make_guinier_plot(ax, qv, xr_components, title=None):
    """
    Create a Guinier plot.
    """
    if title is not None:
        ax.set_title(title)
    ax.set_xlabel(r"$Q^2$")
    ax.set_ylabel(r"$\log(I) - I_0$")

    sg_list = []
    for i, xr_component in enumerate(xr_components):
        data = xr_component.get_jcurve_array()
        pv = data[:,1]
        sg = SimpleGuinier(data)
        sg_list.append(sg)
        try:
            start = sg.guinier_start
            stop = sg.guinier_stop
            for j, slice_ in enumerate([slice(0, int(stop*1.2)), slice(start, stop)]):
                qv2 = qv[slice_]**2
                logy = np.log(pv[slice_])
                color = 'gray' if j == 0 else 'C%d'%(i)
                alpha = 0.5 if j == 0 else 1
                label = None if j == 0 else r"component-%d, $R_g=%.3g$" % (i+1, sg.Rg)
                if j == 0:
                    ax.plot(qv2, logy - np.log(sg.Iz), ":", color=color, alpha=alpha, label=label)
                else:
                    slope = -sg.Rg**2/3
                    gy = qv2 * slope
                    ax.plot(qv2, gy, color=color, alpha=alpha, label=label)
        except Exception as e:
            print(f"make_guinier_plot: Error processing component {i+1}: {e}")

    ax.legend()
    return sg_list

def make_kratky_plot(ax, qv, P, sg_list, title=None):
    """
    Create a Kratky plot.
    """
    if title is not None:
        ax.set_title(title)
    ax.set_xlabel("$QR_g$")
    ax.set_ylabel(r"$(QR_g)^2 \times I(Q)/I_0$")

    for i, sg in enumerate(sg_list):
        if sg.Rg is not None:
            qrg = qv*sg.Rg
            pv = P[:,i]
            ax.plot(qrg, qrg**2*pv/sg.Iz, ":", color='C%d'%(i), label="component-%d" % (i+1))

    px = np.sqrt(3)
    py = 3/np.e
    ax.axvline(px, ls=":", color="gray")
    ax.axhline(py, ls=":", color="gray")
    ax.axhline(0, color="red", alpha=0.5)

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    dy = (ymax - ymin)*0.01
    ax.text(px, ymin+dy, r"$ \sqrt{3} $", ha="right")
    ax.text(xmax, py+2*dy, r"$ 3/e $", ha="right")

    ax.legend()

def plot_components_impl(decomposition, **kwargs):
    debug = kwargs.get('debug', False)


    fig = plt.figure(figsize=(16, 8))
    title = kwargs.get('title', None)
    if title is not None:
        fig.suptitle(title)

    axes = create_axes(fig)

    ax1 = axes[0,0]
    ax2 = axes[1,0]

    # UV Elution Curve
    plot_elution_curve(ax1, decomposition.uv_icurve, decomposition.uv_ccurves, title="Elution Curves", ylabel="Absorbance")

    # XR Elution Curve
    axt = plot_elution_curve(ax2, decomposition.xr_icurve, decomposition.xr_ccurves, ylabel="Scattering Intensity", **kwargs)

    # Paired Ranges
    pairedranges = kwargs.get('pairedranges', None)
    if pairedranges is not None:
        x = decomposition.xr_icurve.x
        mapping = decomposition.mapping
        uv_ylim = ax1.get_ylim()
        xr_ylim = ax2.get_ylim()
        for prange in pairedranges:
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
    wv = decomposition.uv.wv
    uv_matrices = decomposition.get_uv_matrices(debug=debug)
    M, C, P = uv_matrices[0:3]
    for i, pv in enumerate(P.T):
        ax3.plot(wv, pv, ":", color='C%d'%(i), label="component-%d" % (i+1))
    ax3.legend()

    # XR Scattering Curves
    ax4.set_xlabel(r"Q $[\AA^{-1}]$")
    ax4.set_ylabel(r"$\log_{10}(I)$")

    qv = decomposition.xr.qv
    xr_matrices = decomposition.get_xr_matrices(debug=debug)
    M, C, P = xr_matrices[0:3]
    for i, pv in enumerate(P.T):
        ax4.plot(qv, pv, ":", color='C%d'%(i), label="component-%d" % (i+1))
    ax4.legend()

    ax5 = axes[0,2]
    ax6 = axes[1,2]

    # Guinier Plot
    sg_list = make_guinier_plot(ax5, qv, decomposition.get_xr_components(), title="XR Guinier/Kratky Plots")

    # Kratky Plot
    make_kratky_plot(ax6, qv, P, sg_list)

    fig.tight_layout()
    fig.subplots_adjust(wspace=1.5)

    if debug:
        plt.show()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, (ax1, ax2, axt))