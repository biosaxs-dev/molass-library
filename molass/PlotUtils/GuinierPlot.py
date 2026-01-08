"""
PlotUtils.GuinierPlot.py
"""
import numpy as np
import matplotlib.pyplot as plt

def guinier_plot_general(q, I, e, guinier_region, plot_region, axes=None, debug=False):
    if axes is None:
        fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12,10))
    else:
        fig = axes[0,0].figure

    lnI = np.log(I)
    q2 = q**2
    plot_start, plot_stop = plot_region
    print(f"Guinier plot range: start={plot_start}, stop={plot_stop}")
    ax1, ax2 = axes[0,:]
    ax1.plot(q, I, 'o', markersize=3, label='Data')
    ax1.set_title('Linear Plot')
    ax1.set_xlabel(r"$q [\AA^{-1}]$")
    ax1.set_ylabel(r'$Intensity$')
    ax2.set_yscale('log')
    ax2.set_xscale('log')
    ax2.set_title('Logarithmic Plot')
    ax2.set_xlabel(r"$q [\AA^{-1}]$")
    ax2.plot(q, I, 'o', markersize=3, label='Data')
    plot_slice = slice(plot_start, plot_stop)
    ax3, ax4 = axes[1,:]
    ax3.plot(q[plot_slice], I[plot_slice], 'o', markersize=3, label='Data')
    gindeces = np.array(guinier_region)
    ax3.axvspan(*q[gindeces], color='red', alpha=0.2, label='Guinier region')
    ax3.set_title('Linear Plot')
    ax3.set_xlabel(r"$q [\AA^{-1}]$")
    ax3.set_ylabel(r'$Intensity$')
    ax4.plot(q2[plot_slice], lnI[plot_slice], 'o', markersize=3, label='Data')
    ax4.axvspan(*q2[gindeces], color='red', alpha=0.2, label='Guinier region')
    ax4.set_xlabel(r"$q^2 [\AA^{-2}]$")
    ax4.set_ylabel(r'$\ln(Intensity)$')
    ax4.set_title('Guinier Plot')
    ax4.grid()
    ax4.legend()
    fig.tight_layout()
    return fig, axes

def guinier_plot_impl(sg, axes=None, debug=False):
    q = sg.x_
    if sg.Rg is None:
        start= 0
        stop = len(q)//8
    else:
        start = sg.guinier_start
        stop = sg.guinier_stop
    guinier_plot_general(q, sg.y_, sg.e_, (start, stop), (0, len(q)//8), axes=axes, debug=debug)

def inspect_guinier_plot(sg, debug=False):
    if debug:
        print("Inspecting Guinier plot...")
        from importlib import reload
        import molass_legacy.GuinierAnalyzer.SimpleGuinier
        reload(molass_legacy.GuinierAnalyzer.SimpleGuinier)
    from molass_legacy.GuinierAnalyzer.SimpleGuinier import SimpleGuinier
    data = np.array([sg.x_, sg.y_, sg.e_]).T
    sg = SimpleGuinier(data)
    print(f"Guinier Rg: {sg.Rg}")
    from alsaker_rg import estimate_Rg
    Rg1, se1, t1, cp2_1, sp1 = estimate_Rg(data, num_reps=1, starting_value=5, make_plots=False)
    print(f"Estimated Rg: {Rg1} ± {se1}")
    print(f"Guinier region: {sp1[0]}, t1: {t1}")
    if debug:
        import molass.Guinier.SimpleFallback
        reload(molass.Guinier.SimpleFallback)
    from molass.Guinier.SimpleFallback import SimpleFallback, compute_rg
    sgf = SimpleFallback(data)
    sgf.estimate()
    print(f"Fallback Guinier Rg: {sgf.result['Rg']}, q_start: {sgf.result['q_start']}, q_stop: {sgf.result['q_stop']}, q_rg_max: {sgf.result['q_rg_max']}, n_points: {sgf.result['n_points']}")
    if debug:
        sgf.plot()
    guinier_region = (sgf.result['q_start'], sgf.result['q_stop'])
    plot_region = (0, data.shape[0]//8)
    if debug:
        guinier_plot_general(*data.T, guinier_region, plot_region, debug=debug)
    gslice = slice(*guinier_region)
    qw2 = data[gslice, 0]**2
    lnI = np.log(data[gslice, 1])
    weights = (data[gslice, 2] / data[gslice, 1])**2
    rg = compute_rg(qw2, lnI, weights)
    print(f"Computed Rg from fallback region: {guinier_region}, rg: {rg}")