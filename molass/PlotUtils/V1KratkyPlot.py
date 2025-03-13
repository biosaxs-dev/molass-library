"""
PlotUtils.V1KratkyPlot.py
"""
import numpy as np

def kratky_plot(ax, qv, y, rg, I0, color, markersize=3):
    if rg is None:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Not Available", ha="center", va="center")
    else:
        ax.set_xlabel(r"$QR_g$")
        ax.set_ylabel(r"$(QR_g)^2 \times I(Q)/I(0)$")
        qrg = qv*rg
        ax.plot(qrg, qrg**2*y/I0, 'o', markersize=markersize, color=color)

        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        ymin = min(-0.15, ymin)
        ymax = max(1.2, ymax)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)

        px = np.sqrt(3)
        py = 3/np.e
        ax.plot([px, px], [ymin, ymax], ":", color="gray")
        ax.plot([xmin, xmax], [py, py], ":", color="gray")

        dy = (ymax - ymin)*0.01
        ax.text(px, ymin+dy, r"$ \sqrt{3} $", ha="right")
        ax.text(xmax, py+2*dy, r"$ 3/e $", ha="right")

        ax.plot([xmin, xmax], [0, 0], color='red')