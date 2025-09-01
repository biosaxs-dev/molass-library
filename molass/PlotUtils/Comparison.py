"""
    PlotUtils.Comparison.py
"""

import matplotlib.pyplot as plt

def comparison_plot(decompositions, **kwargs):
    """
    Create a comparison plot for a pair of decompositions.
    """
    assert len(decompositions) == 2, "This function is designed for comparing two decompositions."
    debug = kwargs.get('debug', False)
    if debug:
        from importlib import reload
        import molass.PlotUtils.DecompositionPlot
        reload(molass.PlotUtils.DecompositionPlot)
    from molass.PlotUtils.DecompositionPlot import create_axes, plot_elution_curve, make_guinier_plot, make_kratky_plot

    fig = plt.figure(figsize=(16, 8))
    title = kwargs.get('title', None)
    if title is not None:
        fig.suptitle(title)

    d1 = decompositions[0]
    d2 = decompositions[1]
    show_proportions = kwargs.get('show_proportions', False)
    if show_proportions:
        proportions1 = d1.get_proportions()
        proportions2 = d2.get_proportions()
        print("Proportions of the first decomposition:", proportions1)
        print("Proportions of the second decomposition:", proportions2)
        subwkargs1 = {'proportions': proportions1}
        subwkargs2 = {'proportions': proportions2}
    else:
        subwkargs1 = {}
        subwkargs2 = {}
    axes = create_axes(fig, row_titles=["XR1", "XR2"])
    ax1 = axes[0,0]
    ax2 = axes[1,0]
    plot_elution_curve(ax1, d1.xr_icurve, d1.xr_ccurves, title="Elution Curves", ylabel="Scattering Intensity", **subwkargs1)
    plot_elution_curve(ax2, d2.xr_icurve, d2.xr_ccurves, ylabel="Scattering Intensity", **subwkargs2)

    # Guinier Plot2
    ax3 = axes[0,1]
    ax4 = axes[1,1]
    qv = d1.xr.qv
    sg_list1 = make_guinier_plot(ax3, qv, d1.get_xr_components(), title="Guinier Plots")
    sg_list2 = make_guinier_plot(ax4, qv, d2.get_xr_components())

    # Kratky Plots
    ax5 = axes[0,2]
    ax6 = axes[1,2]
    xr_matrices1 = d1.get_xr_matrices(debug=debug)
    make_kratky_plot(ax5, qv, xr_matrices1[2], sg_list1, title="Kratky Plots")
    xr_matrices2 = d2.get_xr_matrices(debug=debug)
    make_kratky_plot(ax6, qv, xr_matrices2[2], sg_list2)

    fig.tight_layout()