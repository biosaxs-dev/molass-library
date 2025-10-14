"""
PlotUtils.V1GuinierPlot.py
"""
import numpy as np

def guinier_plot(ax, qv, y, color, interval, markersize):
    qq = qv**2
    logy = np.log(y)

    ax.set_xlabel("$Q^2$")
    ax.set_ylabel("$ln(I)$")
    ax.plot(qq, logy, 'o', markersize=3, color=color)

    if interval is not None:
        gf, gt = interval
        ax.plot(qq[[gf,gt]],logy[[gf,gt]], '-o', color='cyan')
        set_limits_from_interval(ax, qq, logy, interval)

    # ax.set_xticklabels(ax1.get_xticks(), rotation=30)
    ax.set_xticks(ax.get_xticks()[::2])

def set_limits_from_interval(ax, qq, logy, interval):
    gf, gt = interval
    gxmin = qq[0]
    gxmax = qq[gt]
    gymin = logy[gt]
    gymax = np.max(logy[0:gt])

    def extend(ex_ratio, side, margin, vmin, vmax):
        if side == "top":
            w1 = 1 + margin - ex_ratio
        else:
            w1 = -margin
        retmin = vmin*(1-w1) + vmax*w1
        w2 = ex_ratio + w1
        retmax = vmin*(1-w2) + vmax*w2
        return retmin, retmax

    try:
        ax.set_xlim(extend(1.5, 'left', 0.2, gxmin, gxmax))
        ax.set_ylim(extend(2.0, 'top', 0.5, gymin, gymax))
    except Exception as exc:
        from KekLib.ExceptionTracebacker import log_exception
        log_exception(None, "failed to set limits: (gxmin, gxmax)=(%s, %s), (gymin, gymax)=(%s, %s)" % (str(gxmin), str(gxmax), str(gymin), str(gymax)))