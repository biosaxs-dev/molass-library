"""
    DmaxEstimation.py

    Copyright (c) 2020-2025, SAXS Team, KEK-PF
"""
import numpy as np
from .denss.core import Sasrec, estimate_dmax as _core_estimate_dmax, estimate_rough_alpha
from molass.SAXS.DenssUtils import fit_data_impl

def estimate_dmax(Iq, dmax=None, clean_up=True):
    """Estimate Dmax using the vendored DENSS v1.8.8 algorithm (denss.core.estimate_dmax).

    Ported 2026-09-16 from the old hand-copied pre-v1.8.8 algorithm (see molass-researcher
    experiments/39_denss_study/39a_dmax_alpha_estimator.ipynb for the comparison that motivated
    this). Also reconstructs the oversmoothed P(r) that the new algorithm uses internally to
    decide where to truncate Dmax (lobe decomposition) -- core.estimate_dmax computes this only
    to make that decision, then discards it (its returned sasrec always has alpha=0). Rebuilding
    it here is purely for the GUI illustration panel below; it does not affect the D value.
    """
    D, sasrec = _core_estimate_dmax(Iq, dmax=dmax, clean_up=clean_up)
    rough_alpha = estimate_rough_alpha(Iq, D, Sasrec)
    sasrec_smooth = Sasrec(Iq, D=D, qc=None, alpha=rough_alpha * 50.0, extrapolate=True)
    D_idx = int(np.argmin(np.abs(sasrec_smooth.r - D)))
    return D, sasrec, [sasrec_smooth.r, sasrec_smooth.P, D_idx]

def plot_input(ax, data, in_file):
    q = data[:,0]
    a = data[:,1]
    e = data[:,2]

    sasrec, work_info = fit_data_impl(q, a, e, in_file)
    qc = sasrec.qc
    ac = sasrec.Ic
    ec = work_info.Icerr

    ax.set_yscale('log')
    ax.set_xlabel('q', fontsize=16)
    ax.set_ylabel('log(I)', fontsize=16)

    ax.plot(q, a, color='C1', label="input data")
    # ax1.plot(qc, ac, color='C2', label="fitted data")

    ax.legend(fontsize=16)

def illustrate_dmax(ax, data):
    D_, sasrec_, info = estimate_dmax(data)
    r = sasrec_.r
    P = sasrec_.P
    r_, Psmooth, D_idx = info

    ax.set_xlabel('r', fontsize=16)
    ax.set_ylabel('P', fontsize=16)

    ax.plot(r, P, color='C1', label="P(r) from input data")
    ax.plot(r_, Psmooth, color='C2', label="oversmoothed P(r) (Dmax decision basis)")
    ax.plot(r_[D_idx], Psmooth[D_idx], 'o', color='red', label='estimated Dmax')

    ax.legend(fontsize=16)
    ymin, ymax = ax.get_ylim()
    hymax = ymax*0.5
    if ymin < 0 and abs(ymin) > hymax:
        # cut off the negative part of P(r) if it is too large
        ymin = -abs(hymax)
        ax.set_ylim(ymin, ymax)

def demo(in_file):
    import molass_legacy.KekLib.DebugPlot as plt    
    print(in_file)
    data = np.loadtxt(in_file)

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(16,7))
    fig.suptitle("Denss Dmax Estimation Illustrated", fontsize=30)

    plot_input(ax1, data, in_file)
    illustrate_dmax(ax2, data)

    fig.tight_layout()
    fig.subplots_adjust(top=0.9)
    plt.show()
