"""
    Stochastic.ColumnSliceStates.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np

def draw_slice_states_impl(fig, ax, grains, pxv, pyv, inmobile_states, debug=False):
    print("draw_slice_states_impl")
 
    dy = 0.01

    maxy = np.max(pyv) + dy
    miny = np.min(pyv) - dy
    print("maxy, miny=",maxy, miny)

    hist, bin_edges = np.histogram(pyv, bins=20)
    print("hist, bin_edges=",hist, bin_edges)
    dy = bin_edges[1] - bin_edges[0]

    def draw_impl(ax):
        ax.set_ylim(0, 1)
        ax.set_xlim(0, np.max(hist)*1.1)
        starts = np.zeros(len(hist))
        height = (bin_edges[1] - bin_edges[0])*0.9
        for label, pyv_ in [('Mobile Phase', pyv[inmobile_states]), ('Stationary Phase', pyv[~inmobile_states])]:
            hist_, _ = np.histogram(pyv_, bins=bin_edges)
            ax.barh(bin_edges[:-1] + dy/2, hist_, left=starts, height=height, label=label)
            starts += hist_
        ax.legend(fontsize=16)

    if debug:
        import molass_legacy.KekLib.DebugPlot as plt
        with plt.Dp():
            fig_, ax_ = plt.subplots(figsize=(8,20))
            draw_impl(ax_)
            fig_.tight_layout()
            plt.show()
    else:
        ax.cla()
        draw_impl(ax)
        fig.canvas.draw()