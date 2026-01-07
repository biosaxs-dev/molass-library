"""
PlotUtils.GuinierPlot.py
"""
import numpy as np
import matplotlib.pyplot as plt

def guinier_plot_impl(sg, axes=None, debug=False):
    if axes is None:
        fig, axes = plt.subplots(ncols=2, figsize=(12,5))
    else:
        fig = axes[0].figure
    q = sg.x_
    I = sg.y_
    lnI = np.log(I)
    q2 = q**2
    if sg.Rg is None:
        start= 0
        stop = len(q)//8
    else:
        start = sg.guinier_start
        stop = sg.guinier_stop
    print(f"Guinier plot range: start={start}, stop={stop}, Rg={sg.Rg}")
    gslice = slice(start, stop)
    ax1, ax2 = axes
    ax1.plot(q[gslice], I[gslice], 'o', markersize=3, label='Data')
    ax1.set_title('Linear Plot')
    ax1.set_xlabel(r"$q [\AA^{-1}]$")
    ax1.set_ylabel(r'$Intensity$')
    ax2.plot(q2[gslice], lnI[gslice], 'o', markersize=3, label='Data')
    ax2.set_xlabel(r"$q^2 [\AA^{-2}]$")
    ax2.set_ylabel(r'$\ln(Intensity)$')
    ax2.set_title('Guinier Plot')
    ax2.grid()
    ax2.legend()
    return fig, axes

def inspect_guinier_plot(sg, debug=False):
    if debug:
        print("Inspecting Guinier plot...")
        from importlib import reload
        import molass_legacy.GuinierAnalyzer.SimpleGuinier
        reload(molass_legacy.GuinierAnalyzer.SimpleGuinier)
    from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
    data = np.array([sg.x_, sg.y_, sg.e_]).T
    sg = SimpleGuinier(data, debug_plot=debug)