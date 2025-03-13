"""
PlotUtils.SsMatrixDataPlot.py

This module contains the functions,
which are used to plot the data of a SsMatrixData object.
"""

import matplotlib.pyplot as plt
from molass.PlotUtils.MatrixPlot import simple_plot_3d

def plot_3d_sa_impl(xr, debug=False):
    uqrange = xr.get_usable_qrange(return_object=True)
    icurve = uqrange.icurve
    i = icurve.get_max_i()
    jcurve = xr.get_jcurve(i)
    qv, jy = jcurve.get_xy()
    sg = uqrange.pre_rg.sg
    j1 = sg.guinier_start
    j2 = sg.guinier_stop
    if debug:
        fig = plt.figure(figsize=(15, 4))
        ax0 = fig.add_subplot(131)
        ax1 = fig.add_subplot(132)
        ax = fig.add_subplot(133, projection='3d')
        ix, iy = icurve.get_xy()
        ax0.plot(ix, iy)
        ax0.axvline(ix[i], ls=":", color='r')
        ax1.plot(qv, jy)
        for j in j1, j2:
            ax1.axvline(qv[j], color='yellow')
    else:
        fig, ax = plt.subplots(subplot_kw=dict(projection='3d')) 


    labelkwarg = dict(fontsize=9)
    tickkwarg = dict(labelsize=9)

    ax.set_title("Small Angle Region")
    ax.set_xlabel("Q", **labelkwarg)
    ax.set_ylabel("frames", **labelkwarg)
    ax.set_zlabel("scattering", **labelkwarg)
    simple_plot_3d(ax, xr.M, x=xr.iv, y=xr.jv)
    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis.set_tick_params(**tickkwarg)

    fig.tight_layout()

    from molass.PlotUtils.PlotResult import PlotResult
    return PlotResult(fig, ax)